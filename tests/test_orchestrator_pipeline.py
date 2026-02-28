import pytest

pytest.importorskip("mistralai")

import server.orchestrator as orchestrator


class _AgentOK:
    def __init__(self, payload):
        self.payload = payload

    async def process(self, _data):
        return self.payload


class _AgentRaises:
    async def process(self, _data):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_pipeline_resilience_with_optional_agent_failure(monkeypatch):
    orchestrator.results_store.clear()
    orchestrator.audio_store.clear()

    monkeypatch.setattr(orchestrator, "language_agent", _AgentOK({"language": "hi", "confidence": 0.9}))
    monkeypatch.setattr(orchestrator, "translation_agent", _AgentOK({"translated_text": "translated claim"}))
    monkeypatch.setattr(
        orchestrator,
        "claim_agent",
        _AgentOK(
            {
                "claims": [{"claim": "translated claim", "type": "factual", "verifiability": "high", "key_entities": []}],
                "main_claim": "translated claim",
            }
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "verdict_agent",
        _AgentOK(
            {
                "verdict": "FALSE",
                "confidence": 0.81,
                "summary": "False claim.",
                "native_summary": "गलत दावा।",
                "key_evidence": ["Trusted sources refute the claim."],
            }
        ),
    )

    orchestrator.source_agent = _AgentRaises()
    orchestrator.media_agent = _AgentOK({"credibility_score": 0.4})
    orchestrator.context_agent = _AgentOK({"known_hoax_match": True, "match_confidence": 0.9})
    orchestrator.expert_agent = _AgentOK({"expert_verdict": "FALSE", "confidence": 0.76})

    async def fake_audio(_text, _lang):
        return None, "disabled", "ElevenLabs credentials are not configured."

    monkeypatch.setattr(orchestrator, "synthesize_verdict_audio", fake_audio)

    vid = "test-pipeline"
    orchestrator.results_store[vid] = {
        "verification_id": vid,
        "status": "processing",
        "input_type": "text",
        "original_text": "original claim",
        "warnings": [],
        "agent_errors": {},
        "stage_timings": {},
        "audio_available": False,
        "audio_status": "pending",
        "audio_message": "",
    }

    await orchestrator._run_pipeline(
        vid,
        text="original claim",
        input_type="text",
        image_data=None,
        mime_type=None,
        ocr_metadata={},
    )

    result = orchestrator.results_store[vid]
    assert result["status"] == "completed"
    assert result["verdict"] == "FALSE"
    assert "source_verification" in result["agent_errors"]
    assert any("source_verification failed" in warning for warning in result["warnings"])
    assert "language_detection" in result["stage_timings"]
    assert result["audio_status"] == "disabled"
