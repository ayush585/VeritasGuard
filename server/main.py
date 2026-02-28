import uuid
import asyncio
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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
    return JSONResponse({
        "verification_id": vid,
        "status": "processing",
        "extracted_text": extracted_text.strip(),
        "ocr_metadata": ocr_metadata,
    })


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
