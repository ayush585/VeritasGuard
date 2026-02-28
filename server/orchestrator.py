import asyncio
import uuid
import traceback
from datetime import datetime

from server.agents.language_detection import LanguageDetectionAgent
from server.agents.translation import TranslationAgent
from server.agents.claim_extraction import ClaimExtractionAgent
from server.agents.verdict import VerdictAgent

# Global agent instances (created once, reused)
language_agent = LanguageDetectionAgent()
translation_agent = TranslationAgent()
claim_agent = ClaimExtractionAgent()
verdict_agent = VerdictAgent()

# Optional P1 agents — imported lazily
source_agent = None
media_agent = None
context_agent = None
expert_agent = None

# In-memory results store
results_store: dict[str, dict] = {}


def _try_load_p1_agents():
    global source_agent, media_agent, context_agent, expert_agent
    try:
        from server.agents.source_verification import SourceVerificationAgent
        source_agent = SourceVerificationAgent()
    except Exception:
        pass
    try:
        from server.agents.media_forensics import MediaForensicsAgent
        media_agent = MediaForensicsAgent()
    except Exception:
        pass
    try:
        from server.agents.context_history import ContextHistoryAgent
        context_agent = ContextHistoryAgent()
    except Exception:
        pass
    try:
        from server.agents.expert_validation import ExpertValidationAgent
        expert_agent = ExpertValidationAgent()
    except Exception:
        pass


async def initialize_agents():
    """Initialize all agents on startup."""
    _try_load_p1_agents()
    agents = [language_agent, translation_agent, claim_agent, verdict_agent]
    for a in [source_agent, media_agent, context_agent, expert_agent]:
        if a is not None:
            agents.append(a)
    await asyncio.gather(*(a.initialize() for a in agents), return_exceptions=True)
    print(f"[Orchestrator] Initialized {len(agents)} agents")


async def verify_text(text: str, verification_id: str | None = None) -> str:
    """Run the full verification pipeline on text input."""
    vid = verification_id or str(uuid.uuid4())
    results_store[vid] = {
        "verification_id": vid,
        "status": "processing",
        "original_text": text,
        "started_at": datetime.utcnow().isoformat(),
        "stage": "language_detection",
    }

    # Run pipeline in background
    asyncio.create_task(_run_pipeline(vid, text))
    return vid


async def verify_image_text(extracted_text: str, verification_id: str | None = None) -> str:
    """Run verification on text extracted from an image."""
    return await verify_text(extracted_text, verification_id)


def get_result(vid: str) -> dict | None:
    return results_store.get(vid)


async def _run_pipeline(vid: str, text: str):
    try:
        # ── Stage 1: Sequential — Language Detection → Translation → Claim Extraction ──
        results_store[vid]["stage"] = "language_detection"
        lang_result = await language_agent.process({"text": text})
        detected_lang = lang_result.get("language", "en")
        results_store[vid]["detected_language"] = detected_lang
        results_store[vid]["language_result"] = lang_result

        results_store[vid]["stage"] = "translation"
        if detected_lang != "en":
            trans_result = await translation_agent.process({
                "text": text,
                "source_language": detected_lang,
                "target_language": "en",
            })
            english_text = trans_result.get("translated_text", text)
        else:
            trans_result = {"translated_text": text, "source_language": "en", "target_language": "en"}
            english_text = text
        results_store[vid]["translated_text"] = english_text
        results_store[vid]["translation_result"] = trans_result

        results_store[vid]["stage"] = "claim_extraction"
        claims_result = await claim_agent.process({
            "text": english_text,
            "original_text": text,
        })
        results_store[vid]["claims"] = claims_result.get("claims", [])
        results_store[vid]["claims_result"] = claims_result

        # ── Stage 2: Parallel — Source, Media, Context, Expert ──
        results_store[vid]["stage"] = "verification"
        parallel_tasks = {}

        if source_agent:
            parallel_tasks["source_verification"] = source_agent.process({
                "text": english_text,
                "claims": claims_result,
            })
        if media_agent:
            parallel_tasks["media_forensics"] = media_agent.process({
                "text": english_text,
                "original_text": text,
            })
        if context_agent:
            parallel_tasks["context_history"] = context_agent.process({
                "text": english_text,
                "original_text": text,
                "claims": claims_result,
            })
        if expert_agent:
            parallel_tasks["expert_validation"] = expert_agent.process({
                "text": english_text,
                "claims": claims_result,
            })

        parallel_results = {}
        if parallel_tasks:
            task_names = list(parallel_tasks.keys())
            task_coros = list(parallel_tasks.values())
            outcomes = await asyncio.gather(*task_coros, return_exceptions=True)
            for name, outcome in zip(task_names, outcomes):
                if isinstance(outcome, Exception):
                    parallel_results[name] = {"error": str(outcome)}
                else:
                    parallel_results[name] = outcome

        results_store[vid]["agent_results"] = parallel_results

        # ── Stage 3: Verdict Synthesis ──
        results_store[vid]["stage"] = "verdict"
        verdict_input = {
            "claims": claims_result,
            "original_text": text,
            "original_language": detected_lang,
            **parallel_results,
        }
        verdict_result = await verdict_agent.process(verdict_input)

        results_store[vid].update({
            "status": "completed",
            "stage": "done",
            "verdict": verdict_result.get("verdict", "UNVERIFIABLE"),
            "confidence": verdict_result.get("confidence", 0.0),
            "summary": verdict_result.get("summary", ""),
            "native_summary": verdict_result.get("native_summary", ""),
            "key_evidence": verdict_result.get("key_evidence", []),
            "verdict_result": verdict_result,
            "completed_at": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        traceback.print_exc()
        results_store[vid].update({
            "status": "error",
            "stage": "error",
            "error": str(e),
        })
