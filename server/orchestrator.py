from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from datetime import datetime
from typing import Any

from server.agents.claim_extraction import ClaimExtractionAgent
from server.agents.language_detection import LanguageDetectionAgent
from server.agents.translation import TranslationAgent
from server.agents.verdict import VerdictAgent
from server.languages import normalize_language_code
from server.utils.audio_tts import synthesize_verdict_audio

# Global agent instances (created once, reused)
language_agent = LanguageDetectionAgent()
translation_agent = TranslationAgent()
claim_agent = ClaimExtractionAgent()
verdict_agent = VerdictAgent()

# Optional P1/P2 agents imported lazily
source_agent = None
media_agent = None
context_agent = None
expert_agent = None

# In-memory stores (demo-mode)
results_store: dict[str, dict[str, Any]] = {}
audio_store: dict[str, bytes] = {}


def _try_load_optional_agents():
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


def _mark_stage_start(result: dict[str, Any], stage: str) -> float:
    result["stage"] = stage
    return time.perf_counter()


def _mark_stage_end(result: dict[str, Any], stage: str, stage_start: float):
    timings = result.setdefault("stage_timings", {})
    timings[stage] = round(time.perf_counter() - stage_start, 3)


def _warn(result: dict[str, Any], message: str):
    warnings = result.setdefault("warnings", [])
    if message not in warnings:
        warnings.append(message)


def _record_agent_error(result: dict[str, Any], agent_name: str, error: Exception | str):
    errors = result.setdefault("agent_errors", {})
    errors[agent_name] = str(error)


async def initialize_agents():
    """Initialize all agents on startup."""
    _try_load_optional_agents()
    agents = [language_agent, translation_agent, claim_agent, verdict_agent]
    for agent in [source_agent, media_agent, context_agent, expert_agent]:
        if agent is not None:
            agents.append(agent)
    await asyncio.gather(*(agent.initialize() for agent in agents), return_exceptions=True)
    print(f"[Orchestrator] Initialized {len(agents)} agents")


async def verify_text(
    text: str,
    verification_id: str | None = None,
    *,
    input_type: str = "text",
    image_data: bytes | None = None,
    mime_type: str | None = None,
    ocr_metadata: dict[str, Any] | None = None,
) -> str:
    """Run the full verification pipeline on input text."""
    vid = verification_id or str(uuid.uuid4())
    results_store[vid] = {
        "verification_id": vid,
        "status": "processing",
        "input_type": input_type,
        "original_text": text,
        "started_at": datetime.utcnow().isoformat(),
        "stage": "language_detection",
        "warnings": [],
        "agent_errors": {},
        "stage_timings": {},
        "audio_available": False,
        "audio_status": "pending",
        "audio_message": "Audio generation not started.",
    }
    if ocr_metadata:
        results_store[vid]["ocr_metadata"] = ocr_metadata

    asyncio.create_task(
        _run_pipeline(
            vid,
            text=text,
            input_type=input_type,
            image_data=image_data,
            mime_type=mime_type,
            ocr_metadata=ocr_metadata or {},
        )
    )
    return vid


async def verify_image_text(
    extracted_text: str,
    verification_id: str | None = None,
    *,
    image_data: bytes | None = None,
    mime_type: str | None = None,
    ocr_metadata: dict[str, Any] | None = None,
) -> str:
    """Run verification on text extracted from an image."""
    return await verify_text(
        extracted_text,
        verification_id,
        input_type="image",
        image_data=image_data,
        mime_type=mime_type,
        ocr_metadata=ocr_metadata,
    )


def get_result(vid: str) -> dict[str, Any] | None:
    return results_store.get(vid)


def get_audio(vid: str) -> bytes | None:
    return audio_store.get(vid)


async def _run_pipeline(
    vid: str,
    *,
    text: str,
    input_type: str,
    image_data: bytes | None,
    mime_type: str | None,
    ocr_metadata: dict[str, Any],
):
    result = results_store[vid]
    try:
        # Stage 1: Language detection
        stage_start = _mark_stage_start(result, "language_detection")
        try:
            lang_result = await language_agent.process({"text": text})
            detected_lang = normalize_language_code(lang_result.get("language", "en"))
        except Exception as e:
            _record_agent_error(result, "language_detection", e)
            _warn(result, "Language detection failed, defaulted to English.")
            lang_result = {"language": "en", "confidence": 0.5, "method": "fallback"}
            detected_lang = "en"
        result["detected_language"] = detected_lang
        result["language_result"] = lang_result
        _mark_stage_end(result, "language_detection", stage_start)

        # Stage 2: translation
        stage_start = _mark_stage_start(result, "translation")
        if detected_lang != "en":
            try:
                trans_result = await translation_agent.process(
                    {
                        "text": text,
                        "source_language": detected_lang,
                        "target_language": "en",
                    }
                )
                english_text = trans_result.get("translated_text", text)
            except Exception as e:
                _record_agent_error(result, "translation", e)
                _warn(result, "Translation failed, using original text.")
                trans_result = {
                    "translated_text": text,
                    "source_language": detected_lang,
                    "target_language": "en",
                }
                english_text = text
        else:
            trans_result = {"translated_text": text, "source_language": "en", "target_language": "en"}
            english_text = text
        result["translated_text"] = english_text
        result["translation_result"] = trans_result
        _mark_stage_end(result, "translation", stage_start)

        # Stage 3: claim extraction
        stage_start = _mark_stage_start(result, "claim_extraction")
        try:
            claims_result = await claim_agent.process({"text": english_text, "original_text": text})
            claims = claims_result.get("claims", [])
        except Exception as e:
            _record_agent_error(result, "claim_extraction", e)
            _warn(result, "Claim extraction failed, using raw text as fallback claim.")
            claims_result = {
                "claims": [{"claim": english_text, "type": "factual", "verifiability": "low", "key_entities": []}],
                "main_claim": english_text,
                "category": "other",
            }
            claims = claims_result["claims"]
        result["claims"] = claims
        result["claims_result"] = claims_result
        _mark_stage_end(result, "claim_extraction", stage_start)

        # Stage 4: parallel verification
        stage_start = _mark_stage_start(result, "verification")
        parallel_tasks: dict[str, Any] = {}
        if source_agent:
            parallel_tasks["source_verification"] = source_agent.process({"text": english_text, "claims": claims_result})
        if media_agent:
            parallel_tasks["media_forensics"] = media_agent.process(
                {
                    "text": english_text,
                    "original_text": text,
                    "input_type": input_type,
                    "image_data": image_data,
                    "mime_type": mime_type or "image/png",
                    "ocr_metadata": ocr_metadata,
                }
            )
        if context_agent:
            parallel_tasks["context_history"] = context_agent.process(
                {
                    "text": english_text,
                    "original_text": text,
                    "claims": claims_result,
                }
            )
        if expert_agent:
            parallel_tasks["expert_validation"] = expert_agent.process({"text": english_text, "claims": claims_result})

        parallel_results: dict[str, Any] = {}
        if parallel_tasks:
            names = list(parallel_tasks.keys())
            outcomes = await asyncio.gather(*parallel_tasks.values(), return_exceptions=True)
            for name, outcome in zip(names, outcomes):
                if isinstance(outcome, Exception):
                    _record_agent_error(result, name, outcome)
                    _warn(result, f"{name} failed and was skipped.")
                    parallel_results[name] = {"error": str(outcome)}
                else:
                    parallel_results[name] = outcome
        result["agent_results"] = parallel_results
        source_meta = parallel_results.get("source_verification", {})
        if isinstance(source_meta, dict):
            result["search_provider"] = source_meta.get("search_provider", "none")
            result["search_results_count"] = source_meta.get("search_results_count", 0)
        _mark_stage_end(result, "verification", stage_start)

        # Stage 5: verdict synthesis
        stage_start = _mark_stage_start(result, "verdict")
        verdict_input = {
            "claims": claims_result,
            "original_text": text,
            "original_language": detected_lang,
            **parallel_results,
        }
        try:
            verdict_result = await verdict_agent.process(verdict_input)
        except Exception as e:
            _record_agent_error(result, "verdict", e)
            _warn(result, "Verdict synthesis failed; returned fallback UNVERIFIABLE verdict.")
            verdict_result = {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.2,
                "summary": "Unable to produce a final verdict because of a synthesis error.",
                "native_summary": "Unable to produce a final verdict because of a synthesis error.",
                "key_evidence": [],
                "sources_quality": "none",
            }
        _mark_stage_end(result, "verdict", stage_start)

        # Optional audio synthesis (non-fatal)
        native_or_english_summary = verdict_result.get("native_summary") or verdict_result.get("summary", "")
        audio_bytes, audio_status, audio_message = await synthesize_verdict_audio(native_or_english_summary, detected_lang)
        if audio_bytes:
            audio_store[vid] = audio_bytes
        result.update(
            {
                "audio_available": bool(audio_bytes),
                "audio_status": audio_status,
                "audio_message": audio_message,
            }
        )
        if audio_status == "failed":
            _warn(result, audio_message)

        result.update(
            {
                "status": "completed",
                "stage": "done",
                "verdict": verdict_result.get("verdict", "UNVERIFIABLE"),
                "confidence": verdict_result.get("confidence", 0.0),
                "summary": verdict_result.get("summary", ""),
                "native_summary": verdict_result.get("native_summary", ""),
                "key_evidence": verdict_result.get("key_evidence", []),
                "verdict_result": verdict_result,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        traceback.print_exc()
        result.update({"status": "error", "stage": "error", "error": str(e), "audio_status": "failed"})
