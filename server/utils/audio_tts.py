from __future__ import annotations

import json
import os
from typing import Any

import httpx


def _parse_voice_map(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
    except json.JSONDecodeError:
        pass
    return {}


def _voice_for_language(language_code: str) -> str | None:
    voice_map = _parse_voice_map(os.getenv("ELEVENLABS_VOICE_MAP"))
    if language_code in voice_map:
        return voice_map[language_code]
    return os.getenv("ELEVENLABS_VOICE_ID_DEFAULT")


def _synthesis_payload(text: str) -> dict[str, Any]:
    return {
        "text": text,
        "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.4")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")),
        },
    }


async def synthesize_verdict_audio(text: str, language_code: str) -> tuple[bytes | None, str, str]:
    clean_text = str(text or "").strip()
    if not clean_text:
        return None, "disabled", "No text available for synthesis."

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = _voice_for_language(language_code)
    if not api_key or not voice_id:
        return None, "disabled", "ElevenLabs credentials are not configured."

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=_synthesis_payload(clean_text))
            response.raise_for_status()
            return response.content, "ready", "Audio ready."
    except Exception as e:
        return None, "failed", f"Audio synthesis failed: {e}"
