from typing import Optional

from pydantic import BaseModel


class VerificationRequest(BaseModel):
    text: str
    language: Optional[str] = None


class VerificationResponse(BaseModel):
    verification_id: str
    status: str = "processing"


class VerificationResult(BaseModel):
    verification_id: str
    status: str
    input_type: Optional[str] = None
    original_text: Optional[str] = None
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    claims: Optional[list] = None
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    native_summary: Optional[str] = None
    sources: Optional[list] = None
    agent_results: Optional[dict] = None
    warnings: Optional[list[str]] = None
    agent_errors: Optional[dict[str, str]] = None
    stage_timings: Optional[dict[str, float]] = None
    latency_ms_by_stage: Optional[dict[str, int]] = None
    search_provider: Optional[str] = None
    search_results_count: Optional[int] = None
    deterministic_override_applied: Optional[bool] = None
    override_reason: Optional[str] = None
    override_match_score: Optional[float] = None
    audio_available: Optional[bool] = None
    audio_status: Optional[str] = None
    audio_message: Optional[str] = None
    ocr_metadata: Optional[dict] = None
    error: Optional[str] = None
