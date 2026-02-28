from __future__ import annotations

import asyncio
import os
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


def _load_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


PIPELINE_DEADLINE_SECONDS = _load_float_env("PIPELINE_DEADLINE_SECONDS", 12.0)
STAGE_BUDGETS = {
    "language_detection": _load_float_env("STAGE_BUDGET_LANGUAGE_SECONDS", 0.8),
    "translation": _load_float_env("STAGE_BUDGET_TRANSLATION_SECONDS", 1.5),
    "claim_extraction": _load_float_env("STAGE_BUDGET_CLAIM_SECONDS", 1.5),
    "verification": _load_float_env("STAGE_BUDGET_VERIFICATION_SECONDS", 4.0),
    "verdict": _load_float_env("STAGE_BUDGET_VERDICT_SECONDS", 1.0),
}
OPTIONAL_AGENT_TIMEOUTS = {
    "source_verification": _load_float_env("STAGE_BUDGET_SOURCE_SECONDS", 4.0),
    "media_forensics": _load_float_env("STAGE_BUDGET_MEDIA_SECONDS", 2.0),
    "context_history": _load_float_env("STAGE_BUDGET_CONTEXT_SECONDS", 1.2),
    "expert_validation": _load_float_env("STAGE_BUDGET_EXPERT_SECONDS", 1.5),
}


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
    elapsed = max(0.0, time.perf_counter() - stage_start)
    timings = result.setdefault("stage_timings", {})
    timings[stage] = round(elapsed, 3)
    latency = result.setdefault("latency_ms_by_stage", {})
    latency[stage] = int(elapsed * 1000)


def _warn(result: dict[str, Any], message: str):
    warnings = result.setdefault("warnings", [])
    if message not in warnings:
        warnings.append(message)


def _record_agent_error(result: dict[str, Any], agent_name: str, error: Exception | str):
    errors = result.setdefault("agent_errors", {})
    errors[agent_name] = str(error)


def _remaining_pipeline_budget(result: dict[str, Any]) -> float:
    deadline = float(result.get("_pipeline_deadline_perf", time.perf_counter()))
    return max(0.0, deadline - time.perf_counter())


def _stage_timeout(result: dict[str, Any], stage_name: str, *, minimum: float = 0.15) -> float:
    base = STAGE_BUDGETS.get(stage_name, 1.0)
    remaining = _remaining_pipeline_budget(result)
    if remaining <= 0:
        return minimum
    return max(minimum, min(base, remaining))


async def _run_with_timeout(awaitable: Any, timeout_seconds: float, timeout_label: str):
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f"{timeout_label} timed out after {timeout_seconds:.2f}s") from exc


def _fallback_verdict_from_context(parallel_results: dict[str, Any], original_language: str) -> dict[str, Any]:
    context_result = parallel_results.get("context_history", {}) if isinstance(parallel_results, dict) else {}
    if isinstance(context_result, dict) and context_result.get("known_hoax_match"):
        try:
            score = float(context_result.get("match_confidence", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        if score >= 0.82:
            verdict = "FALSE" if score >= 0.9 else "MOSTLY_FALSE"
            summary = (
                "Known recurring hoax pattern matched in historical records. "
                "This claim is treated as misinformation in degraded mode."
            )
            return {
                "verdict": verdict,
                "confidence": round(min(0.92, max(0.7, score)), 3),
                "summary": summary,
                "native_summary": summary if original_language == "en" else summary,
                "key_evidence": ["Context/history strong match"],
                "sources_quality": "low",
                "deterministic_override_applied": True,
                "override_reason": "context_fallback_override",
                "override_match_score": round(score, 3),
            }
    return {
        "verdict": "UNVERIFIABLE",
        "confidence": 0.2,
        "summary": "Unable to produce a final verdict due to timeout while preserving partial results.",
        "native_summary": "Unable to produce a final verdict due to timeout while preserving partial results.",
        "key_evidence": [],
        "sources_quality": "none",
        "deterministic_override_applied": False,
        "override_reason": "timeout_fallback",
        "override_match_score": None,
    }


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
    created_at = datetime.utcnow().isoformat()
    results_store[vid] = {
        "verification_id": vid,
        "status": "processing",
        "input_type": input_type,
        "original_text": text,
        "started_at": created_at,
        "stage": "language_detection",
        "warnings": [],
        "agent_errors": {},
        "stage_timings": {},
        "latency_ms_by_stage": {},
        "search_provider": "none",
        "search_results_count": 0,
        "audio_available": False,
        "audio_status": "pending",
        "audio_message": "Audio generation not started.",
        "_pipeline_start_perf": time.perf_counter(),
        "_pipeline_deadline_perf": time.perf_counter() + PIPELINE_DEADLINE_SECONDS,
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
    if "_pipeline_deadline_perf" not in result:
        result["_pipeline_start_perf"] = time.perf_counter()
        result["_pipeline_deadline_perf"] = time.perf_counter() + PIPELINE_DEADLINE_SECONDS
    try:
        # Stage 1: Language detection
        stage_start = _mark_stage_start(result, "language_detection")
        try:
            timeout = _stage_timeout(result, "language_detection")
            lang_result = await _run_with_timeout(language_agent.process({"text": text}), timeout, "language_detection")
            detected_lang = normalize_language_code(lang_result.get("language", "en"))
        except Exception as e:
            _record_agent_error(result, "language_detection", e)
            _warn(result, "Language detection failed or timed out; defaulted to English.")
            lang_result = {"language": "en", "confidence": 0.5, "method": "fallback"}
            detected_lang = "en"
        result["detected_language"] = detected_lang
        result["language_result"] = lang_result
        _mark_stage_end(result, "language_detection", stage_start)

        # Stage 2: translation
        stage_start = _mark_stage_start(result, "translation")
        if detected_lang != "en":
            try:
                timeout = _stage_timeout(result, "translation")
                trans_result = await _run_with_timeout(
                    translation_agent.process(
                        {
                            "text": text,
                            "source_language": detected_lang,
                            "target_language": "en",
                        }
                    ),
                    timeout,
                    "translation",
                )
                english_text = trans_result.get("translated_text", text)
            except Exception as e:
                _record_agent_error(result, "translation", e)
                _warn(result, "Translation failed/timed out, using original text.")
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
        compact_mode = detected_lang == "ur"
        if compact_mode:
            _warn(result, "Compact-mode budgets enabled for Urdu/long-tail latency control.")
        try:
            timeout = _stage_timeout(result, "claim_extraction")
            claims_result = await _run_with_timeout(
                claim_agent.process({"text": english_text, "original_text": text}),
                timeout,
                "claim_extraction",
            )
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
        parallel_tasks: dict[str, asyncio.Task] = {}
        verification_timeout = _stage_timeout(result, "verification", minimum=0.4)
        remaining_budget = _remaining_pipeline_budget(result)
        if remaining_budget < 0.6:
            _warn(result, "Skipping optional agents due to exhausted pipeline budget.")
        else:
            if source_agent:
                source_timeout = min(
                    OPTIONAL_AGENT_TIMEOUTS["source_verification"],
                    2.6 if compact_mode else OPTIONAL_AGENT_TIMEOUTS["source_verification"],
                )
                parallel_tasks["source_verification"] = asyncio.create_task(
                    _run_with_timeout(
                        source_agent.process(
                            {
                                "text": english_text,
                                "claims": claims_result,
                                "compact_mode": compact_mode,
                            }
                        ),
                        max(0.3, min(source_timeout, verification_timeout)),
                        "source_verification",
                    )
                )
            if media_agent:
                parallel_tasks["media_forensics"] = asyncio.create_task(
                    _run_with_timeout(
                        media_agent.process(
                            {
                                "text": english_text,
                                "original_text": text,
                                "input_type": input_type,
                                "image_data": image_data,
                                "mime_type": mime_type or "image/png",
                                "ocr_metadata": ocr_metadata,
                            }
                        ),
                        max(0.3, min(OPTIONAL_AGENT_TIMEOUTS["media_forensics"], verification_timeout)),
                        "media_forensics",
                    )
                )
            if context_agent:
                parallel_tasks["context_history"] = asyncio.create_task(
                    _run_with_timeout(
                        context_agent.process(
                            {
                                "text": english_text,
                                "original_text": text,
                                "claims": claims_result,
                            }
                        ),
                        max(0.3, min(OPTIONAL_AGENT_TIMEOUTS["context_history"], verification_timeout)),
                        "context_history",
                    )
                )
            if expert_agent:
                parallel_tasks["expert_validation"] = asyncio.create_task(
                    _run_with_timeout(
                        expert_agent.process(
                            {
                                "text": english_text,
                                "claims": claims_result,
                                "compact_mode": compact_mode,
                            }
                        ),
                        max(0.3, min(OPTIONAL_AGENT_TIMEOUTS["expert_validation"], verification_timeout)),
                        "expert_validation",
                    )
                )

        parallel_results: dict[str, Any] = {}
        if parallel_tasks:
            done, pending = await asyncio.wait(
                set(parallel_tasks.values()),
                timeout=verification_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )

            task_to_name = {task: name for name, task in parallel_tasks.items()}
            for completed_task in done:
                name = task_to_name[completed_task]
                try:
                    outcome = completed_task.result()
                except Exception as e:
                    _record_agent_error(result, name, e)
                    _warn(result, f"{name} failed and was skipped.")
                    parallel_results[name] = {"error": str(e)}
                    continue
                parallel_results[name] = outcome

            for pending_task in pending:
                name = task_to_name[pending_task]
                pending_task.cancel()
                _record_agent_error(result, name, "Timed out in verification stage budget.")
                _warn(result, f"{name} timed out and was skipped.")
                parallel_results[name] = {"error": "Timed out in verification stage budget."}

        result["agent_results"] = parallel_results
        source_meta = parallel_results.get("source_verification", {})
        if isinstance(source_meta, dict):
            result["search_provider"] = source_meta.get("search_provider", "none")
            result["search_results_count"] = source_meta.get("search_results_count", 0)
            for item in source_meta.get("warnings", []) if isinstance(source_meta.get("warnings"), list) else []:
                _warn(result, f"source_verification: {item}")
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
            timeout = _stage_timeout(result, "verdict", minimum=0.35)
            verdict_result = await _run_with_timeout(verdict_agent.process(verdict_input), timeout, "verdict")
        except Exception as e:
            _record_agent_error(result, "verdict", e)
            _warn(result, "Verdict synthesis failed/timed out; returned fallback verdict.")
            verdict_result = _fallback_verdict_from_context(parallel_results, detected_lang)
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
                "deterministic_override_applied": verdict_result.get("deterministic_override_applied", False),
                "override_reason": verdict_result.get("override_reason"),
                "override_match_score": verdict_result.get("override_match_score"),
                "verdict_result": verdict_result,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        traceback.print_exc()
        result.update({"status": "error", "stage": "error", "error": str(e), "audio_status": "failed"})
    finally:
        result.pop("_pipeline_start_perf", None)
        result.pop("_pipeline_deadline_perf", None)
