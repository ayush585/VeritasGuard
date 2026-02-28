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


class _FakeRequest:
    def __init__(self, form_data: dict, headers: dict | None = None, url: str = "https://example.com/webhook/whatsapp"):
        self._form_data = form_data
        self.headers = headers or {}
        self.url = url

    async def form(self):
        return self._form_data


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


@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_signature(monkeypatch):
    monkeypatch.setattr(main_module, "WHATSAPP_VALIDATE_SIGNATURE", True)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-token")

    request = _FakeRequest(
        {"From": "whatsapp:+123", "Body": "hello", "NumMedia": "0"},
        headers={"X-Twilio-Signature": "invalid"},
    )

    with pytest.raises(HTTPException) as exc:
        await main_module.whatsapp_webhook(request)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_text_success(monkeypatch):
    monkeypatch.setattr(main_module, "WHATSAPP_VALIDATE_SIGNATURE", False)
    monkeypatch.setattr(main_module, "_apply_rate_limit", lambda _sender: True)

    async def fake_verify_text(_text, verification_id=None, **_kwargs):
        return verification_id

    async def fake_wait_for_result(_vid, _timeout):
        return {
            "status": "completed",
            "verdict": "FALSE",
            "confidence": 0.91,
            "native_summary": "यह दावा गलत है।",
            "search_provider": "mistral_web_search",
            "search_results_count": 3,
        }

    monkeypatch.setattr(main_module, "verify_text", fake_verify_text)
    monkeypatch.setattr(main_module, "_wait_for_result", fake_wait_for_result)

    request = _FakeRequest({"From": "whatsapp:+123", "Body": "Claim text", "NumMedia": "0"})
    response = await main_module.whatsapp_webhook(request)
    text = response.body.decode("utf-8")
    assert response.media_type == "application/xml"
    assert "VeritasGuard Verdict: FALSE" in text


@pytest.mark.asyncio
async def test_whatsapp_webhook_unsupported_media(monkeypatch):
    monkeypatch.setattr(main_module, "WHATSAPP_VALIDATE_SIGNATURE", False)
    monkeypatch.setattr(main_module, "_apply_rate_limit", lambda _sender: True)

    request = _FakeRequest(
        {
            "From": "whatsapp:+123",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://example.com/test.mp4",
            "MediaContentType0": "video/mp4",
            "AccountSid": "AC1",
        }
    )
    response = await main_module.whatsapp_webhook(request)
    text = response.body.decode("utf-8")
    assert "Unsupported media type" in text
