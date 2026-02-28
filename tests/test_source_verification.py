import json

import pytest

pytest.importorskip("mistralai")

import server.agents.base_agent as base_agent_module


class _DummyClient:
    pass


@pytest.mark.asyncio
async def test_source_verification_graceful_degradation(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.source_verification import SourceVerificationAgent

    agent = SourceVerificationAgent()

    async def fake_search(_query):
        return [], ""

    monkeypatch.setattr(agent, "_search_with_mistral", fake_search)

    result = await agent.process({"text": "Claim text", "claims": {"main_claim": "Claim text"}})
    assert result["consensus"] == "insufficient"
    assert result["search_provider"] == "mistral_web_search"
    assert result["search_attempted"] is True
    assert result["search_results_count"] == 0


@pytest.mark.asyncio
async def test_source_verification_uses_results(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.source_verification import SourceVerificationAgent

    agent = SourceVerificationAgent()
    fake_sources = [
        {"title": "WHO mythbusters", "url": "https://example.org/who", "snippet": "refutes claim"},
        {"title": "PIB fact check", "url": "https://example.org/pib", "snippet": "clarification"},
    ]

    async def fake_search(_query):
        return fake_sources, "Top sources indicate this claim is false."

    async def fake_query(_prompt):
        return json.dumps(
            {
                "source_quality": "high",
                "supporting_sources": fake_sources,
                "consensus": "refutes",
                "analysis": "Credible independent sources refute the claim.",
            }
        )

    monkeypatch.setattr(agent, "_search_with_mistral", fake_search)
    monkeypatch.setattr(agent, "_query", fake_query)

    result = await agent.process({"text": "Claim text", "claims": {"main_claim": "Claim text"}})
    assert result["consensus"] == "refutes"
    assert result["source_quality"] == "high"
    assert result["search_results_count"] == 2
