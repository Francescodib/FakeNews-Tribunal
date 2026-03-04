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
    credibility_tier: str | None = None
    credibility_score: float | None = None
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


# --- Admin ---

class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    is_admin: bool
    is_disabled: bool
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str | None = Field(default=None, min_length=8)
    is_admin: bool | None = None
    is_disabled: bool | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminStatsResponse(BaseModel):
    total_users: int
    total_analyses: int
    analyses_by_status: dict[str, int]
    analyses_by_provider: dict[str, int]


# --- Me ---

class MeResponse(BaseModel):
    id: UUID
    email: str
    is_admin: bool
    is_disabled: bool


# --- Webhook ---

class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=500)
    secret: str | None = Field(default=None, max_length=100)


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    is_active: bool
    created_at: datetime


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    analysis_id: UUID | None
    event: str
    status: str
    attempts: int
    last_attempt_at: datetime | None
    created_at: datetime


# --- Batch ---

class BatchRequest(BaseModel):
    claims: list[str] = Field(..., min_length=1)
    llm_provider: str = Field(default="anthropic")
    llm_model: str | None = None
    language: str = Field(default="it", pattern=r"^[a-z]{2}$")
    max_rounds: int = Field(default=5, ge=1, le=10)


class BatchResponse(BaseModel):
    batch_id: UUID
    analysis_ids: list[UUID]
    status_url: str
    total: int


class BatchStatusResponse(BaseModel):
    id: UUID
    status: str
    total: int
    completed: int
    failed: int
    created_at: datetime
    completed_at: datetime | None
    analysis_ids: list[UUID]


class BatchListResponse(BaseModel):
    items: list[BatchStatusResponse]
    total: int
    page: int
    page_size: int
