import os
import uuid
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.database import init_db, seed_hoaxes
from server.orchestrator import initialize_agents, verify_text, verify_image_text, get_result


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

    # Try OCR
    extracted_text = ""
    try:
        from PIL import Image
        import pytesseract
        import io

        image = Image.open(io.BytesIO(contents))
        # Try Hindi + English OCR
        extracted_text = pytesseract.image_to_string(image, lang="hin+eng")
    except Exception as e:
        print(f"[OCR] Failed: {e}")

    if not extracted_text.strip():
        # Fallback: try Pixtral vision via Mistral
        try:
            import base64
            from server.utils.mistral_client import get_mistral_client

            client = get_mistral_client()
            b64 = base64.b64encode(contents).decode()
            mime = file.content_type or "image/png"

            response = await asyncio.to_thread(
                client.chat.complete,
                model="pixtral-large-latest",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": "Extract ALL text visible in this image. Return only the extracted text, nothing else."},
                    ],
                }],
            )
            extracted_text = response.choices[0].message.content
        except Exception as e:
            print(f"[Pixtral] Failed: {e}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from image")

    vid = str(uuid.uuid4())
    await verify_image_text(extracted_text.strip(), verification_id=vid)
    return JSONResponse({
        "verification_id": vid,
        "status": "processing",
        "extracted_text": extracted_text.strip(),
    })


@app.get("/result/{verification_id}")
async def get_result_endpoint(verification_id: str):
    result = get_result(verification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
