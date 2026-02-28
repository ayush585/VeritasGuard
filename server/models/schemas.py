from pydantic import BaseModel
from typing import Optional


class VerificationRequest(BaseModel):
    text: str
    language: Optional[str] = None


class VerificationResponse(BaseModel):
    verification_id: str
    status: str = "processing"


class VerificationResult(BaseModel):
    verification_id: str
    status: str
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
    error: Optional[str] = None
