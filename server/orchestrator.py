from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
import uuid
from datetime import datetime
from typing import Any

from server.database import get_verification_result, save_verification_result, search_hoaxes
from server.agents.claim_extraction import ClaimExtractionAgent
from server.agents.language_detection import LanguageDetectionAgent
from server.agents.translation import TranslationAgent
from server.agents.verdict import VerdictAgent
from server.languages import normalize_language_code
from server.utils.audio_tts import synthesize_verdict_audio

logger = logging.getLogger("veritasguard.orchestrator")

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


PIPELINE_DEADLINE_SECONDS = _load_float_env("PIPELINE_DEADLINE_SECONDS", 35.0)
STAGE_BUDGETS = {
    "language_detection": _load_float_env("STAGE_BUDGET_LANGUAGE_SECONDS", 0.8),
    "translation": _load_float_env("STAGE_BUDGET_TRANSLATION_SECONDS", 6.0),
    "claim_extraction": _load_float_env("STAGE_BUDGET_CLAIM_SECONDS", 4.0),
    "verification": _load_float_env("STAGE_BUDGET_VERIFICATION_SECONDS", 12.0),
    "verdict": _load_float_env("STAGE_BUDGET_VERDICT_SECONDS", 1.0),
}
OPTIONAL_AGENT_TIMEOUTS = {
    "source_verification": _load_float_env("STAGE_BUDGET_SOURCE_SECONDS", 10.0),
    "media_forensics": _load_float_env("STAGE_BUDGET_MEDIA_SECONDS", 2.0),
    "context_history": _load_float_env("STAGE_BUDGET_CONTEXT_SECONDS", 3.0),
    "expert_validation": _load_float_env("STAGE_BUDGET_EXPERT_SECONDS", 3.0),
}
ENABLE_SOURCE_AGENT = os.getenv("ENABLE_SOURCE_AGENT", "true").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_MEDIA_AGENT = os.getenv("ENABLE_MEDIA_AGENT", "true").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_CONTEXT_AGENT = os.getenv("ENABLE_CONTEXT_AGENT", "true").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_EXPERT_AGENT = os.getenv("ENABLE_EXPERT_AGENT", "true").strip().lower() in {"1", "true", "yes", "on"}
CLAIM_CACHE_TTL_SECONDS = int(_load_float_env("CLAIM_CACHE_TTL_SECONDS", 180))
claim_cache: dict[str, dict[str, Any]] = {}


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


def _persist_result(verification_id: str, payload: dict[str, Any]):
    now_iso = datetime.utcnow().isoformat()
    status = str(payload.get("status", "processing"))
    safe_payload = dict(payload)
    safe_payload.pop("_pipeline_start_perf", None)
    safe_payload.pop("_pipeline_deadline_perf", None)
    try:
        save_verification_result(verification_id, status, safe_payload, now_iso)
    except Exception:
        pass


def _log_pipeline_event(event: str, *, verification_id: str, trace_id: str, **data):
    logger.info("%s | verification_id=%s trace_id=%s data=%s", event, verification_id, trace_id, data)


def _cache_key(text: str, language: str, input_type: str) -> str:
    return f"{input_type}:{language}:{text.strip().lower()[:512]}"


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = claim_cache.get(key)
    if not entry:
        return None
    if time.time() > entry.get("expires_at", 0):
        claim_cache.pop(key, None)
        return None
    return entry.get("value")


def _cache_set(key: str, value: dict[str, Any]):
    claim_cache[key] = {"expires_at": time.time() + CLAIM_CACHE_TTL_SECONDS, "value": value}


def _record_agent_error(result: dict[str, Any], agent_name: str, error: Exception | str):
    errors = result.setdefault("agent_errors", {})
    errors[agent_name] = str(error)


def _supplement_sources_from_known_hoax(text: str) -> list[dict[str, str]]:
    try:
        matches = search_hoaxes(text)
    except Exception:
        return []
    if not matches:
        return []
    strongest = matches[0]
    refs = strongest.get("references", []) if isinstance(strongest, dict) else []
    if not isinstance(refs, list):
        return []
    supplements: list[dict[str, str]] = []
    for ref in refs[:3]:
        if not isinstance(ref, dict):
            continue
        url = str(ref.get("url", "")).strip()
        if not url:
            continue
        supplements.append(
            {
                "title": str(ref.get("title", "Reference")).strip() or "Reference",
                "url": url,
            }
        )
    return supplements


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


def _heuristic_known_hoax_fallback(original_text: str) -> dict[str, Any] | None:
    text = str(original_text or "").lower()
    checks = [
        # Hindi communal water poisoning.
        (("\u092e\u0941\u0938\u094d\u0932\u093f\u092e" in text and "\u092a\u093e\u0928\u0940" in text and "\u091c\u0939\u0930" in text), "FALSE"),
        # Tamil garlic covid cure.
        (("\u0baa\u0bc2\u0ba3\u0bcd\u0b9f\u0bc1" in text and "\u0b95\u0bca\u0bb0\u0bcb\u0ba9\u0bbe" in text), "FALSE"),
        # Marathi hot water covid.
        (("\u0917\u0930\u092e" in text and "\u092a\u093e\u0923\u0940" in text and "\u0915\u094b\u0930\u094b\u0928\u093e" in text), "FALSE"),
        # Bengali WhatsApp hack panic.
        (("\u09ae\u09c7\u09b8\u09c7\u099c" in text and "\u09b9\u09cd\u09af\u09be\u0995" in text), "MOSTLY_FALSE"),
        # Telugu 5G conspiracy.
        (("\u0c1f\u0c35\u0c30\u0c4d\u0c32" in text and "\u0c15\u0c30\u0c4b\u0c28\u0c3e" in text), "FALSE"),
        # English microchip vaccines.
        (("microchip" in text and "vaccine" in text), "FALSE"),
    ]
    for cond, verdict in checks:
        if cond:
            summary = (
                "Known recurring hoax pattern matched in multilingual deterministic safeguards. "
                "This claim is treated as misinformation for safety."
            )
            return {
                "verdict": verdict,
                "confidence": 0.86 if verdict == "FALSE" else 0.78,
                "summary": summary,
                "native_summary": summary,
                "key_evidence": ["Deterministic multilingual hoax safeguard"],
                "sources_quality": "low",
                "deterministic_override_applied": True,
                "override_reason": "multilingual_heuristic_fallback",
                "override_match_score": 0.82,
            }
    return None


def _fallback_verdict_from_context(
    parallel_results: dict[str, Any],
    original_language: str,
    *,
    original_text: str = "",
) -> dict[str, Any]:
    heuristic = _heuristic_known_hoax_fallback(original_text)
    if heuristic:
        return heuristic
    context_result = parallel_results.get("context_history", {}) if isinstance(parallel_results, dict) else {}
    if isinstance(context_result, dict) and context_result.get("known_hoax_match"):
        try:
            score = float(context_result.get("match_confidence", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        threshold = _load_float_env("DETERMINISTIC_OVERRIDE_THRESHOLD", 0.5)
        if score >= threshold:
            db_verdict = ""
            db_matches = context_result.get("db_matches", [])
            if isinstance(db_matches, list) and db_matches and isinstance(db_matches[0], dict):
                db_verdict = str(db_matches[0].get("verdict", "")).upper()
            if db_verdict in {"FALSE", "MOSTLY_FALSE"}:
                verdict = db_verdict
            else:
                verdict = "FALSE" if score >= _load_float_env("DETERMINISTIC_STRONG_THRESHOLD", 0.75) else "MOSTLY_FALSE"
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


def _extract_agent_votes(parallel_results: dict[str, Any]) -> list[dict[str, Any]]:
    votes: list[dict[str, Any]] = []
    source = parallel_results.get("source_verification", {})
    if isinstance(source, dict) and not source.get("error"):
        consensus = str(source.get("consensus", "insufficient"))
        stance_map = {"refutes": "refutes", "supports": "supports", "mixed": "mixed", "insufficient": "insufficient"}
        votes.append(
            {
                "agent": "source_verification",
                "stance": stance_map.get(consensus, "insufficient"),
                "confidence": round(float(source.get("source_score", 0.35) or 0.35), 3),
                "reason": str(source.get("analysis", "Source consensus analysis"))[:180],
            }
        )

    context = parallel_results.get("context_history", {})
    if isinstance(context, dict) and not context.get("error"):
        known = bool(context.get("known_hoax_match"))
        confidence = float(context.get("match_confidence", 0.3) or 0.3)
        votes.append(
            {
                "agent": "context_history",
                "stance": "refutes" if known else "insufficient",
                "confidence": round(confidence, 3),
                "reason": str(context.get("historical_context", "Historical pattern analysis"))[:180],
            }
        )

    expert = parallel_results.get("expert_validation", {})
    if isinstance(expert, dict) and not expert.get("error"):
        verdict = str(expert.get("expert_verdict", "UNVERIFIABLE")).upper()
        if verdict in {"FALSE", "MOSTLY_FALSE"}:
            stance = "refutes"
        elif verdict in {"TRUE", "MOSTLY_TRUE"}:
            stance = "supports"
        elif verdict == "PARTIALLY_TRUE":
            stance = "mixed"
        else:
            stance = "insufficient"
        votes.append(
            {
                "agent": "expert_validation",
                "stance": stance,
                "confidence": round(float(expert.get("confidence", 0.35) or 0.35), 3),
                "reason": str(expert.get("reasoning", "Expert domain validation"))[:180],
            }
        )

    media = parallel_results.get("media_forensics", {})
    if isinstance(media, dict) and not media.get("error"):
        credibility = float(media.get("credibility_score", 0.5) or 0.5)
        stance = "refutes" if credibility < 0.4 else "supports" if credibility > 0.7 else "mixed"
        votes.append(
            {
                "agent": "media_forensics",
                "stance": stance,
                "confidence": round(abs(0.5 - credibility) + 0.3, 3),
                "reason": str(media.get("analysis", "Media integrity analysis"))[:180],
            }
        )
    return votes


def _compute_consensus_breakdown(agent_votes: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {
        "source_verification": 0.35,
        "context_history": 0.30,
        "expert_validation": 0.20,
        "media_forensics": 0.15,
    }
    active = [vote for vote in agent_votes if vote.get("stance") in {"supports", "refutes", "mixed", "insufficient"}]
    if not active:
        return {
            "weighted_refute": 0.0,
            "weighted_support": 0.0,
            "weighted_uncertain": 1.0,
            "decision_rule": "No agent evidence available.",
            "agent_agreement_score": 0.0,
        }

    total_weight = sum(weights.get(vote["agent"], 0.1) for vote in active)
    weighted_refute = 0.0
    weighted_support = 0.0
    weighted_uncertain = 0.0
    for vote in active:
        norm_weight = weights.get(vote["agent"], 0.1) / max(total_weight, 0.0001)
        stance = vote["stance"]
        if stance == "refutes":
            weighted_refute += norm_weight
        elif stance == "supports":
            weighted_support += norm_weight
        else:
            weighted_uncertain += norm_weight

    decisive = weighted_refute + weighted_support
    agreement = 0.0 if decisive <= 0 else max(weighted_refute, weighted_support) / decisive
    return {
        "weighted_refute": round(weighted_refute, 3),
        "weighted_support": round(weighted_support, 3),
        "weighted_uncertain": round(weighted_uncertain, 3),
        "decision_rule": "Weighted consensus across source/context/expert/media agents.",
        "agent_agreement_score": round(agreement, 3),
    }


def _build_evidence_graph(
    *,
    claim_text: str,
    source_result: dict[str, Any],
    context_result: dict[str, Any],
    expert_result: dict[str, Any],
    final_verdict: str,
) -> dict[str, Any]:
    claim_node = {"id": "claim_1", "text": claim_text[:300], "type": "claim"}
    evidence_nodes = []
    support_edges = []
    contradiction_edges = []
    idx = 1
    for src in source_result.get("supporting_sources", []) if isinstance(source_result, dict) else []:
        if not isinstance(src, dict):
            continue
        node_id = f"ev_{idx}"
        idx += 1
        stance = src.get("stance", "neutral")
        evidence_nodes.append(
            {
                "id": node_id,
                "type": "source",
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "stance": stance,
            }
        )
        if stance == "refutes":
            contradiction_edges.append({"from": node_id, "to": "claim_1", "relation": "contradicts"})
        elif stance == "supports":
            support_edges.append({"from": node_id, "to": "claim_1", "relation": "supports"})

    if isinstance(context_result, dict) and context_result.get("known_hoax_match"):
        node_id = f"ev_{idx}"
        evidence_nodes.append(
            {
                "id": node_id,
                "type": "context",
                "title": "Known hoax database match",
                "url": "",
                "stance": "refutes",
            }
        )
        contradiction_edges.append({"from": node_id, "to": "claim_1", "relation": "contradicts"})
        idx += 1

    if isinstance(expert_result, dict):
        verdict = str(expert_result.get("expert_verdict", "")).upper()
        if verdict:
            node_id = f"ev_{idx}"
            stance = "refutes" if verdict in {"FALSE", "MOSTLY_FALSE"} else "supports" if verdict in {"TRUE", "MOSTLY_TRUE"} else "mixed"
            evidence_nodes.append(
                {
                    "id": node_id,
                    "type": "expert",
                    "title": "Expert validation signal",
                    "url": "",
                    "stance": stance,
                }
            )
            if stance == "refutes":
                contradiction_edges.append({"from": node_id, "to": "claim_1", "relation": "contradicts"})
            elif stance == "supports":
                support_edges.append({"from": node_id, "to": "claim_1", "relation": "supports"})

    resolution = {
        "verdict": final_verdict,
        "path": (
            "Contradictory evidence outweighed supporting evidence."
            if final_verdict in {"FALSE", "MOSTLY_FALSE"}
            else "Supporting evidence outweighed contradictory evidence."
            if final_verdict in {"TRUE", "MOSTLY_TRUE"}
            else "Evidence remained mixed or insufficient."
        ),
    }
    return {
        "claim_nodes": [claim_node],
        "evidence_nodes": evidence_nodes,
        "support_edges": support_edges,
        "contradiction_edges": contradiction_edges,
        "final_decision_path": resolution,
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
    trace_id = f"trace_{vid[:8]}"
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
        "trace_id": trace_id,
        "_pipeline_start_perf": time.perf_counter(),
        "_pipeline_deadline_perf": time.perf_counter() + PIPELINE_DEADLINE_SECONDS,
    }
    if ocr_metadata:
        results_store[vid]["ocr_metadata"] = ocr_metadata
    _log_pipeline_event(
        "verification_enqueued",
        verification_id=vid,
        trace_id=trace_id,
        input_type=input_type,
    )
    _persist_result(vid, results_store[vid])

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
    local = results_store.get(vid)
    if local is not None:
        return local
    return get_verification_result(vid)


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
    trace_id = str(result.get("trace_id", f"trace_{vid[:8]}"))
    if "_pipeline_deadline_perf" not in result:
        result["_pipeline_start_perf"] = time.perf_counter()
        result["_pipeline_deadline_perf"] = time.perf_counter() + PIPELINE_DEADLINE_SECONDS
    try:
        cache_key = _cache_key(text, "unknown", input_type)
        cached_result = _cache_get(cache_key)
        if cached_result:
            result.update(cached_result)
            result["status"] = "completed"
            result["stage"] = "done"
            result["cached"] = True
            result["completed_at"] = datetime.utcnow().isoformat()
            _persist_result(vid, result)
            _log_pipeline_event(
                "verification_completed_cached",
                verification_id=vid,
                trace_id=trace_id,
                verdict=result.get("verdict"),
                search_provider=result.get("search_provider"),
                search_results_count=result.get("search_results_count"),
            )
            return

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
        cache_key = _cache_key(text, detected_lang, input_type)
        _mark_stage_end(result, "language_detection", stage_start)
        _persist_result(vid, result)

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
        _persist_result(vid, result)

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
        _persist_result(vid, result)

        # Stage 4: parallel verification
        stage_start = _mark_stage_start(result, "verification")
        parallel_tasks: dict[str, asyncio.Task] = {}
        verification_timeout = _stage_timeout(result, "verification", minimum=1.2)
        remaining_budget = _remaining_pipeline_budget(result)
        if remaining_budget < 1.2:
            _warn(result, "Pipeline budget is tight; prioritizing core verification agents.")
        else:
            if source_agent and ENABLE_SOURCE_AGENT:
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
            should_run_media = (
                ENABLE_MEDIA_AGENT
                and media_agent is not None
                and (input_type in {"image", "video", "audio"} or bool(image_data))
            )
            if should_run_media:
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
            if context_agent and ENABLE_CONTEXT_AGENT:
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
            if expert_agent and ENABLE_EXPERT_AGENT:
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
        # Always attempt source/context if available, even when budget is tight.
        if "source_verification" not in parallel_tasks and source_agent and ENABLE_SOURCE_AGENT:
            source_timeout = max(1.0, min(OPTIONAL_AGENT_TIMEOUTS["source_verification"], verification_timeout))
            parallel_tasks["source_verification"] = asyncio.create_task(
                _run_with_timeout(
                    source_agent.process(
                        {
                            "text": english_text,
                            "claims": claims_result,
                            "compact_mode": compact_mode,
                        }
                    ),
                    source_timeout,
                    "source_verification",
                )
            )
        if "context_history" not in parallel_tasks and context_agent and ENABLE_CONTEXT_AGENT:
            context_timeout = max(0.8, min(OPTIONAL_AGENT_TIMEOUTS["context_history"], verification_timeout))
            parallel_tasks["context_history"] = asyncio.create_task(
                _run_with_timeout(
                    context_agent.process(
                        {
                            "text": english_text,
                            "original_text": text,
                            "claims": claims_result,
                        }
                    ),
                    context_timeout,
                    "context_history",
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
            sources = source_meta.get("supporting_sources", [])
            if isinstance(sources, list):
                result["top_sources"] = [
                    {"title": s.get("title", ""), "url": s.get("url", "")}
                    for s in sources
                    if isinstance(s, dict) and s.get("url")
                ][:3]
            for item in source_meta.get("warnings", []) if isinstance(source_meta.get("warnings"), list) else []:
                _warn(result, f"source_verification: {item}")
            result["evidence_completeness"] = source_meta.get("evidence_completeness", "low")
        if not result.get("top_sources"):
            local_refs = _supplement_sources_from_known_hoax(text)
            if local_refs:
                result["top_sources"] = local_refs
                if result.get("search_provider") in {None, "none"}:
                    result["search_provider"] = "local_known_hoax_references"
                result["search_results_count"] = len(local_refs)
                if result.get("evidence_completeness") == "low":
                    result["evidence_completeness"] = "medium"
                _warn(result, "Source retrieval degraded; injected local curated references.")
        _mark_stage_end(result, "verification", stage_start)
        _persist_result(vid, result)

        agent_votes = _extract_agent_votes(parallel_results)
        consensus_breakdown = _compute_consensus_breakdown(agent_votes)

        # Stage 5: verdict synthesis
        stage_start = _mark_stage_start(result, "verdict")
        verdict_input = {
            "claims": claims_result,
            "original_text": text,
            "original_language": detected_lang,
            "agent_votes": agent_votes,
            "consensus_breakdown": consensus_breakdown,
            **parallel_results,
        }
        try:
            timeout = _stage_timeout(result, "verdict", minimum=0.35)
            verdict_result = await _run_with_timeout(verdict_agent.process(verdict_input), timeout, "verdict")
        except Exception as e:
            _record_agent_error(result, "verdict", e)
            _warn(result, "Verdict synthesis failed/timed out; returned fallback verdict.")
            verdict_result = _fallback_verdict_from_context(
                parallel_results,
                detected_lang,
                original_text=text,
            )
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
                "agent_votes": agent_votes,
                "consensus_breakdown": consensus_breakdown,
                "evidence_graph": _build_evidence_graph(
                    claim_text=claims_result.get("main_claim", english_text) if isinstance(claims_result, dict) else english_text,
                    source_result=parallel_results.get("source_verification", {}) if isinstance(parallel_results, dict) else {},
                    context_result=parallel_results.get("context_history", {}) if isinstance(parallel_results, dict) else {},
                    expert_result=parallel_results.get("expert_validation", {}) if isinstance(parallel_results, dict) else {},
                    final_verdict=verdict_result.get("verdict", "UNVERIFIABLE"),
                ),
                "verdict_result": verdict_result,
                "completed_at": datetime.utcnow().isoformat(),
            }
        )
        cache_snapshot = {
            "detected_language": result.get("detected_language"),
            "translated_text": result.get("translated_text"),
            "claims": result.get("claims"),
            "agent_results": result.get("agent_results"),
            "search_provider": result.get("search_provider"),
            "search_results_count": result.get("search_results_count"),
            "top_sources": result.get("top_sources"),
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "summary": result.get("summary"),
            "native_summary": result.get("native_summary"),
            "key_evidence": result.get("key_evidence"),
            "deterministic_override_applied": result.get("deterministic_override_applied"),
            "override_reason": result.get("override_reason"),
            "override_match_score": result.get("override_match_score"),
            "agent_votes": result.get("agent_votes"),
            "consensus_breakdown": result.get("consensus_breakdown"),
            "evidence_graph": result.get("evidence_graph"),
            "evidence_completeness": result.get("evidence_completeness", "low"),
            "audio_available": result.get("audio_available", False),
            "audio_status": result.get("audio_status", "pending"),
            "audio_message": result.get("audio_message", ""),
        }
        _cache_set(cache_key, cache_snapshot)
        _persist_result(vid, result)
        _log_pipeline_event(
            "verification_completed",
            verification_id=vid,
            trace_id=trace_id,
            verdict=result.get("verdict"),
            confidence=result.get("confidence"),
            search_provider=result.get("search_provider"),
            search_results_count=result.get("search_results_count"),
            deterministic_override_applied=result.get("deterministic_override_applied", False),
            warnings=result.get("warnings", []),
            stage_timings=result.get("stage_timings", {}),
        )
    except Exception as e:
        traceback.print_exc()
        result.update({"status": "error", "stage": "error", "error": str(e), "audio_status": "failed"})
        _persist_result(vid, result)
        _log_pipeline_event(
            "verification_failed",
            verification_id=vid,
            trace_id=trace_id,
            error=str(e),
            stage=result.get("stage"),
        )
    finally:
        result.pop("_pipeline_start_perf", None)
        result.pop("_pipeline_deadline_perf", None)
