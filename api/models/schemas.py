from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class VerdictLabel(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIABLE = "UNVERIFIABLE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"


class Source(BaseModel):
    url: str
    title: str
    snippet: str
    domain: str
    retrieved_at: str
    credibility_note: str | None = None


class DebateRound(BaseModel):
    round_number: int
    researcher_report: str
    researcher_sources: list[Source]
    advocate_challenge: str
    advocate_counter_sources: list[Source]
    judge_continuation_reason: str | None


class Verdict(BaseModel):
    label: VerdictLabel
    confidence: float
    summary: str
    reasoning: str
    supporting_sources: list[Source]
    contradicting_sources: list[Source]
    total_rounds: int
    processing_time_ms: int


class AnalysisResult(BaseModel):
    id: UUID
    claim: str
    created_at: datetime
    status: str
    debate: list[DebateRound]
    verdict: Verdict | None
    llm_provider: str
    llm_model: str
    error: str | None = None


# --- Request / Response ---

class AnalysisRequest(BaseModel):
    claim: str = Field(..., min_length=10, max_length=2000)
    language: str = Field(default="it", pattern=r"^[a-z]{2}$")
    llm_provider: str = Field(default="anthropic")
    llm_model: str | None = None
    max_rounds: int = Field(default=5, ge=1, le=10)


class AnalysisCreatedResponse(BaseModel):
    analysis_id: UUID
    status_url: str


class AnalysisListResponse(BaseModel):
    items: list[AnalysisResult]
    total: int
    page: int
    page_size: int


# --- Auth ---

class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
