import pytest

pytest.importorskip("mistralai")

import server.agents.base_agent as base_agent_module


class _DummyClient:
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        ("এই দাবি মিথ্যা", "bn"),
        ("ಇದು ಸುಳ್ಳು ಸುದ್ದಿ", "kn"),
        ("ਇਹ ਝੂਠੀ ਖ਼ਬਰ ਹੈ", "pa"),
        ("یہ جھوٹی خبر ہے", "ur"),
        ("ഇത് വ്യാജ വാർത്തയാണ്", "ml"),
        ("ଏହା ଭୁଲ ଖବର", "or"),
    ],
)
async def test_script_detection_for_multiple_languages(monkeypatch, text, expected_code):
    monkeypatch.setattr(base_agent_module, "get_mistral_client", lambda: _DummyClient())
    from server.agents.language_detection import LanguageDetectionAgent

    agent = LanguageDetectionAgent()

    async def no_llm(_text):
        return None, 0.0

    monkeypatch.setattr(agent, "_llm_disambiguation", no_llm)

    result = await agent.process({"text": text})
    assert result["language"] == expected_code
