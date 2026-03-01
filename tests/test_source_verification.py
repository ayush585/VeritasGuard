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
        return [], "", "tool unavailable"

    monkeypatch.setattr(agent, "_search_with_mistral", fake_search)

    result = await agent.process({"text": "Claim text", "claims": {"main_claim": "Claim text"}})
    assert result["consensus"] == "insufficient"
    assert result["search_provider"] == "mistral_web_search"
    assert result["search_attempted"] is True
    assert result["search_results_count"] == 0
    assert result["source_quality"] == "none"
    assert result["warnings"]


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
        return fake_sources, "Top sources indicate this claim is false.", None

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
    assert result["source_quality"] in {"high", "medium"}
    assert result["search_results_count"] == 2
    assert result["supporting_sources"][0]["publisher"]
    assert result["supporting_sources"][0]["credibility_tier"] in {"high", "medium", "low"}


@pytest.mark.asyncio
async def test_source_verification_google_fallback(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.source_verification import SourceVerificationAgent

    agent = SourceVerificationAgent()
    agent.enable_google_fallback = True
    agent.google_search_available = True

    async def fake_search(_query):
        return [], "", "mistral unavailable"

    async def fake_google(_query):
        return [{"title": "PIB", "url": "https://pib.gov.in/example", "snippet": "Refutes the claim"}]

    async def fake_query(_prompt):
        return json.dumps(
            {
                "source_quality": "high",
                "supporting_sources": [],
                "consensus": "refutes",
                "analysis": "Fallback source used.",
            }
        )

    monkeypatch.setattr(agent, "_search_with_mistral", fake_search)
    monkeypatch.setattr(agent, "_search_with_google", fake_google)
    monkeypatch.setattr(agent, "_query", fake_query)

    result = await agent.process({"text": "Claim text", "claims": {"main_claim": "Claim text"}})
    assert result["search_provider"] in {
        "google_custom_search_fallback",
        "mistral_web_search+google_custom_search_fallback",
    }
    assert result["search_results_count"] == 1


@pytest.mark.asyncio
async def test_source_verification_tavily_fallback(monkeypatch):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.source_verification import SourceVerificationAgent

    agent = SourceVerificationAgent()
    agent.enable_tavily_fallback = True
    agent.tavily_search_available = True
    agent.enable_google_fallback = False

    async def fake_search(_query):
        return [], "", "mistral unavailable"

    async def fake_tavily(_query):
        return [{"title": "WHO", "url": "https://www.who.int/example", "snippet": "Refutes myth"}]

    async def fake_query(_prompt):
        return json.dumps(
            {
                "source_quality": "high",
                "supporting_sources": [],
                "consensus": "refutes",
                "analysis": "Tavily fallback source used.",
            }
        )

    monkeypatch.setattr(agent, "_search_with_mistral", fake_search)
    monkeypatch.setattr(agent, "_search_with_tavily", fake_tavily)
    monkeypatch.setattr(agent, "_query", fake_query)

    result = await agent.process({"text": "Claim text", "claims": {"main_claim": "Claim text"}})
    assert "tavily_search_fallback" in result["search_provider"]
    assert result["search_results_count"] == 1
