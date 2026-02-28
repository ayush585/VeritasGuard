import pytest
import asyncio

from server.utils.audio_tts import synthesize_verdict_audio


def test_audio_tts_returns_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID_DEFAULT", raising=False)

    audio, status, message = asyncio.run(synthesize_verdict_audio("hello", "en"))
    assert audio is None
    assert status == "disabled"
    assert "not configured" in message.lower()
