import asyncio
import base64
import hashlib
import hmac
import html
import os
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from server.database import init_db, seed_hoaxes
from server.orchestrator import (
    get_audio,
    get_result,
    initialize_agents,
    verify_image_text,
    verify_text,
)

WHATSAPP_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
WHATSAPP_MEDIA_MAX_BYTES = int(os.getenv("WHATSAPP_MEDIA_MAX_BYTES", str(4 * 1024 * 1024)))
WHATSAPP_MEDIA_TIMEOUT_SECONDS = float(os.getenv("WHATSAPP_MEDIA_TIMEOUT_SECONDS", "8"))
WHATSAPP_MAX_WAIT_SECONDS = float(os.getenv("WHATSAPP_MAX_WAIT_SECONDS", "12"))
WHATSAPP_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("WHATSAPP_RATE_LIMIT_WINDOW_SECONDS", "60"))
WHATSAPP_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("WHATSAPP_RATE_LIMIT_MAX_REQUESTS", "5"))
WHATSAPP_VALIDATE_SIGNATURE = os.getenv("WHATSAPP_VALIDATE_SIGNATURE", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_whatsapp_rate_limit: dict[str, list[float]] = {}


async def _extract_text_with_mistral_ocr(contents: bytes, mime_type: str) -> tuple[str, dict]:
    from server.utils.mistral_client import get_mistral_client

    client = get_mistral_client()
    b64 = base64.b64encode(contents).decode()
    data_url = f"data:{mime_type};base64,{b64}"

    # Prefer dedicated OCR API if available.
    if hasattr(client, "ocr") and hasattr(client.ocr, "process"):
        try:
            response = await asyncio.to_thread(
                client.ocr.process,
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": data_url},
            )
            pages = getattr(response, "pages", None)
            if pages is None and isinstance(response, dict):
                pages = response.get("pages", [])
            extracted_parts = []
            for page in pages or []:
                markdown = getattr(page, "markdown", None)
                if markdown is None and isinstance(page, dict):
                    markdown = page.get("markdown", "")
                if markdown:
                    extracted_parts.append(str(markdown).strip())
            extracted = "\n\n".join(part for part in extracted_parts if part)
            if extracted.strip():
                return extracted.strip(), {"provider": "mistral_ocr", "method": "ocr.process"}
        except Exception as e:
            print(f"[Mistral OCR] Failed: {e}")

    # Fallback to vision completion for extraction.
    try:
        response = await asyncio.to_thread(
            client.chat.complete,
            model="pixtral-large-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {
                            "type": "text",
                            "text": "Extract ALL text visible in this image. Return only extracted text.",
                        },
                    ],
                }
            ],
        )
        extracted_text = response.choices[0].message.content
        if extracted_text and str(extracted_text).strip():
            return str(extracted_text).strip(), {"provider": "pixtral_vision", "method": "chat.complete"}
    except Exception as e:
        print(f"[Pixtral OCR fallback] Failed: {e}")

    return "", {"provider": "none", "method": "unavailable"}


def _extract_text_with_tesseract(contents: bytes) -> tuple[str, dict]:
    try:
        from PIL import Image
        import io
        import pytesseract

        image = Image.open(io.BytesIO(contents))
        text_hi_en = pytesseract.image_to_string(image, lang="hin+eng")
        text_en = pytesseract.image_to_string(image, lang="eng")
        extracted = text_hi_en if len(text_hi_en.strip()) >= len(text_en.strip()) else text_en
        if extracted.strip():
            return extracted.strip(), {"provider": "tesseract", "method": "hin+eng"}
    except Exception as e:
        print(f"[Tesseract OCR fallback] Failed: {e}")
    return "", {"provider": "none", "method": "failed"}


def _twiml_message(body: str) -> Response:
    escaped = html.escape(body or "")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>'
    return Response(content=xml, media_type="application/xml")


def _is_twilio_signature_valid(url: str, params: dict[str, str], signature: str, auth_token: str) -> bool:
    # Twilio signature: base64(HMAC-SHA1(auth_token, url + sorted(params)))
    concatenated = url + "".join(f"{key}{params[key]}" for key in sorted(params.keys()))
    digest = hmac.new(auth_token.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


def _apply_rate_limit(sender: str) -> bool:
    now = time.time()
    entries = _whatsapp_rate_limit.setdefault(sender, [])
    recent = [ts for ts in entries if now - ts <= WHATSAPP_RATE_LIMIT_WINDOW_SECONDS]
    if len(recent) >= WHATSAPP_RATE_LIMIT_MAX_REQUESTS:
        _whatsapp_rate_limit[sender] = recent
        return False
    recent.append(now)
    _whatsapp_rate_limit[sender] = recent
    return True


async def _download_twilio_media(
    media_url: str,
    *,
    account_sid: str,
    auth_token: str,
) -> tuple[bytes | None, str | None, str | None]:
    if not media_url:
        return None, None, "Missing media URL."

    parsed = urlparse(media_url)
    if parsed.scheme not in {"http", "https"}:
        return None, None, "Unsupported media URL scheme."

    auth = (account_sid, auth_token) if account_sid and auth_token else None
    try:
        async with httpx.AsyncClient(timeout=WHATSAPP_MEDIA_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(media_url, auth=auth)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            content = response.content
            if len(content) > WHATSAPP_MEDIA_MAX_BYTES:
                return None, content_type, f"Media too large ({len(content)} bytes)."
            return content, content_type, None
    except Exception as e:
        return None, None, f"Failed to download media: {e}"


async def _wait_for_result(verification_id: str, timeout_seconds: float) -> dict | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = get_result(verification_id)
        if result and result.get("status") in {"completed", "error"}:
            return result
        await asyncio.sleep(0.5)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Server] Initializing database...")
    init_db()
    seed_hoaxes()
    print("[Server] Initializing agents...")
    await initialize_agents()
    print("[Server] Ready!")
    yield
    # Shutdown
    print("[Server] Shutting down.")


app = FastAPI(
    title="VeritasGuard",
    description="Multi-lingual misinformation verification system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "VeritasGuard", "version": "1.0.0"}


@app.post("/verify/text")
async def verify_text_endpoint(text: str = Form(...)):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    vid = str(uuid.uuid4())
    await verify_text(text.strip(), verification_id=vid)
    return JSONResponse({"verification_id": vid, "status": "processing"})


@app.post("/verify/image")
async def verify_image_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    mime_type = file.content_type or "image/png"

    # Mistral-first OCR path.
    extracted_text, ocr_metadata = await _extract_text_with_mistral_ocr(contents, mime_type)

    # Non-Mistral fallback only if Mistral OCR path failed.
    if not extracted_text.strip():
        extracted_text, fallback_metadata = _extract_text_with_tesseract(contents)
        if extracted_text.strip():
            ocr_metadata = fallback_metadata

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from image")

    vid = str(uuid.uuid4())
    await verify_image_text(
        extracted_text.strip(),
        verification_id=vid,
        image_data=contents,
        mime_type=mime_type,
        ocr_metadata=ocr_metadata,
    )
    return JSONResponse(
        {
            "verification_id": vid,
            "status": "processing",
            "extracted_text": extracted_text.strip(),
            "ocr_metadata": ocr_metadata,
        }
    )


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    signature = request.headers.get("X-Twilio-Signature", "")

    if WHATSAPP_VALIDATE_SIGNATURE and auth_token:
        if not _is_twilio_signature_valid(str(request.url), params, signature, auth_token):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    sender = params.get("From", "unknown")
    if not _apply_rate_limit(sender):
        return _twiml_message("Rate limit reached. Please wait a minute before sending another message.")

    body = params.get("Body", "").strip()
    try:
        num_media = int(params.get("NumMedia", "0") or 0)
    except ValueError:
        num_media = 0

    if not body and num_media <= 0:
        return _twiml_message("Please send a text or image to verify.")

    verification_id = str(uuid.uuid4())

    if num_media > 0:
        account_sid = params.get("AccountSid", "")
        media_processed = False
        media_error = None
        for index in range(num_media):
            media_url = params.get(f"MediaUrl{index}", "")
            media_type = params.get(f"MediaContentType{index}", "").lower()
            if media_type not in WHATSAPP_ALLOWED_MIME:
                media_error = f"Unsupported media type: {media_type or 'unknown'}"
                continue

            media_bytes, detected_mime, download_error = await _download_twilio_media(
                media_url,
                account_sid=account_sid,
                auth_token=auth_token,
            )
            if download_error:
                media_error = download_error
                continue

            mime_type = detected_mime or media_type or "image/jpeg"
            extracted_text, ocr_metadata = await _extract_text_with_mistral_ocr(media_bytes or b"", mime_type)
            if not extracted_text.strip():
                extracted_text, fallback_metadata = _extract_text_with_tesseract(media_bytes or b"")
                if extracted_text.strip():
                    ocr_metadata = fallback_metadata
            if not extracted_text.strip():
                media_error = "Could not extract text from image."
                continue

            await verify_image_text(
                extracted_text.strip(),
                verification_id=verification_id,
                image_data=media_bytes,
                mime_type=mime_type,
                ocr_metadata=ocr_metadata,
            )
            media_processed = True
            break

        if not media_processed:
            if body:
                await verify_text(body, verification_id=verification_id)
            else:
                return _twiml_message(media_error or "Unsupported or unreadable media. Send a clear image or text.")
    else:
        await verify_text(body, verification_id=verification_id)

    result = await _wait_for_result(verification_id, WHATSAPP_MAX_WAIT_SECONDS)
    if not result or result.get("status") != "completed":
        return _twiml_message(
            f"Analyzing your message. Verification ID: {verification_id}. Please check back in a few seconds."
        )

    verdict = result.get("verdict", "UNVERIFIABLE")
    confidence = float(result.get("confidence", 0.0) or 0.0)
    summary = (result.get("native_summary") or result.get("summary") or "No summary available.").strip()
    response_text = (
        f"VeritasGuard Verdict: {verdict} ({confidence:.0%})\n"
        f"{summary}\n"
        f"Search: {result.get('search_provider', 'n/a')} ({result.get('search_results_count', 0)} sources)"
    )
    return _twiml_message(response_text)


@app.get("/result/{verification_id}")
async def get_result_endpoint(verification_id: str):
    result = get_result(verification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    return JSONResponse(result)


@app.get("/result/{verification_id}/audio")
async def get_result_audio_endpoint(verification_id: str):
    result = get_result(verification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Verification not found")

    audio_bytes = get_audio(verification_id)
    if not audio_bytes:
        status = result.get("audio_status", "unavailable")
        raise HTTPException(status_code=409, detail=f"Audio not available: {status}")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="{verification_id}.mp3"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
