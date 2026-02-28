import pytest
from fastapi import HTTPException

pytest.importorskip("mistralai")
pytest.importorskip("sqlalchemy")

import server.main as main_module


class _FakeUploadFile:
    def __init__(self, content: bytes, content_type: str = "image/png"):
        self._content = content
        self.content_type = content_type

    async def read(self):
        return self._content


@pytest.mark.asyncio
async def test_verify_image_prefers_mistral_ocr(monkeypatch):
    async def fake_mistral_ocr(_contents, _mime):
        return "extracted text", {"provider": "mistral_ocr", "method": "ocr.process"}

    def fake_tesseract(_contents):
        raise AssertionError("Tesseract fallback should not be used when Mistral OCR works.")

    captured = {}

    async def fake_verify_image_text(text, verification_id=None, **kwargs):
        captured["text"] = text
        captured["kwargs"] = kwargs
        return verification_id

    monkeypatch.setattr(main_module, "_extract_text_with_mistral_ocr", fake_mistral_ocr)
    monkeypatch.setattr(main_module, "_extract_text_with_tesseract", fake_tesseract)
    monkeypatch.setattr(main_module, "verify_image_text", fake_verify_image_text)

    file = _FakeUploadFile(b"fakeimage", content_type="image/png")
    response = await main_module.verify_image_endpoint(file=file)
    payload = response.body.decode("utf-8")

    assert response.status_code == 200
    assert "mistral_ocr" in payload
    assert captured["text"] == "extracted text"
    assert captured["kwargs"]["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_verify_image_uses_tesseract_fallback(monkeypatch):
    async def fake_mistral_ocr(_contents, _mime):
        return "", {"provider": "none", "method": "unavailable"}

    def fake_tesseract(_contents):
        return "tesseract text", {"provider": "tesseract", "method": "hin+eng"}

    captured = {}

    async def fake_verify_image_text(text, verification_id=None, **kwargs):
        captured["text"] = text
        captured["kwargs"] = kwargs
        return verification_id

    monkeypatch.setattr(main_module, "_extract_text_with_mistral_ocr", fake_mistral_ocr)
    monkeypatch.setattr(main_module, "_extract_text_with_tesseract", fake_tesseract)
    monkeypatch.setattr(main_module, "verify_image_text", fake_verify_image_text)

    file = _FakeUploadFile(b"fakeimage", content_type="image/png")
    response = await main_module.verify_image_endpoint(file=file)
    payload = response.body.decode("utf-8")

    assert response.status_code == 200
    assert "tesseract" in payload
    assert captured["text"] == "tesseract text"


@pytest.mark.asyncio
async def test_result_audio_endpoint_unavailable(monkeypatch):
    monkeypatch.setattr(main_module, "get_result", lambda _id: {"audio_status": "disabled"})
    monkeypatch.setattr(main_module, "get_audio", lambda _id: None)

    with pytest.raises(HTTPException) as exc:
        await main_module.get_result_audio_endpoint("abc")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_result_audio_endpoint_success(monkeypatch):
    monkeypatch.setattr(main_module, "get_result", lambda _id: {"audio_status": "ready"})
    monkeypatch.setattr(main_module, "get_audio", lambda _id: b"mp3-bytes")

    response = await main_module.get_result_audio_endpoint("abc")
    assert response.media_type == "audio/mpeg"
    assert response.body == b"mp3-bytes"
