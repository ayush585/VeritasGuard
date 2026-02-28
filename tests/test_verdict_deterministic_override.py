import json

import pytest

pytest.importorskip("mistralai")

import server.agents.base_agent as base_agent_module


class _DummyClient:
    pass


@pytest.mark.asyncio
async def test_verdict_agent_applies_deterministic_override(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.verdict import VerdictAgent

    agent = VerdictAgent()
    result = await agent.process(
        {
            "claims": {"main_claim": "Muslims are poisoning water"},
            "original_text": "Muslims are poisoning water",
            "original_language": "en",
            "source_verification": {"source_quality": "low"},
            "context_history": {
                "known_hoax_match": True,
                "match_confidence": 0.91,
                "risk_category": "communal",
                "db_matches": [
                    {
                        "claim": "Muslims are poisoning water supplies",
                        "explanation": "Recurring communal hoax",
                        "keyword_hits": 2,
                        "overlap_score": 0.55,
                        "combined_score": 0.91,
                    }
                ],
            },
        }
    )
    assert result["deterministic_override_applied"] is True
    assert result["verdict"] in {"FALSE", "MOSTLY_FALSE"}
    assert result["override_reason"] == "known_hoax_high_confidence"


@pytest.mark.asyncio
async def test_verdict_agent_no_override_when_confidence_low(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.verdict import VerdictAgent

    agent = VerdictAgent()

    async def fake_query(_prompt):
        return json.dumps(
            {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.31,
                "summary": "Insufficient evidence.",
                "key_evidence": [],
                "sources_quality": "none",
            }
        )

    monkeypatch.setattr(agent, "_query", fake_query)
    result = await agent.process(
        {
            "claims": {"main_claim": "Claim"},
            "original_text": "Claim",
            "original_language": "en",
            "context_history": {
                "known_hoax_match": True,
                "match_confidence": 0.45,
                "risk_category": "health",
                "db_matches": [
                    {"keyword_hits": 0, "overlap_score": 0.1, "combined_score": 0.45},
                ],
            },
        }
    )
    assert result["deterministic_override_applied"] is False
    assert result["verdict"] == "UNVERIFIABLE"
