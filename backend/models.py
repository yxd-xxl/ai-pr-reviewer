"""Pydantic models — request/response schemas for all endpoints."""

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────
class OAuthCallbackRequest(BaseModel):
    code: str
    state: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    login: str
    name: str | None = None
    avatar_url: str | None = None
    organizations: list[str] = []


# ── Repos ─────────────────────────────────────
class RepoInfo(BaseModel):
    full_name: str
    private: bool = False
    language: str | None = None
    open_issues_count: int = 0
    description: str | None = None


class PRInfo(BaseModel):
    number: int
    title: str
    html_url: str
    user: dict
    state: str
    draft: bool = False
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    comments: int = 0
    created_at: str = ""


# ── Review ────────────────────────────────────
class ReviewRequest(BaseModel):
    pr_url: str
    categories: str = "all"
    mode: str = "balanced"
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    min_confidence: float = 0.0
    max_inline_comments: int = 0


class FindingResponse(BaseModel):
    severity: str
    category: str
    title: str
    description: str
    suggestion: str
    confidence: float
    location: dict
    evidence: str | None = None
    fix_patch: str | None = None
    fix_verified: bool = False
    analyzer: str | None = None
    lifecycle_state: str = "detected"


class ReviewResponse(BaseModel):
    status: str
    pr: dict | None = None
    files_count: int = 0
    findings: list[FindingResponse] = []
    summary: str = ""
    warnings: list[str] = []
    risk_score: int = 0
    risk_level: str = "low"
    timing: dict = {}


# ── History ───────────────────────────────────
class ReviewHistoryItem(BaseModel):
    id: int
    pr_url: str
    pr_title: str | None = None
    repo: str | None = None
    findings_count: int = 0
    risk_score: int = 0
    mode: str = "balanced"
    categories: str = "all"
    created_at: str = ""


# ── Feedback ──────────────────────────────────
class FeedbackRequest(BaseModel):
    fingerprint: str
    state: str
    reason: str = ""


# ── Settings ──────────────────────────────────
class SettingsUpdate(BaseModel):
    min_confidence: float | None = None
    max_inline_comments: int | None = None
    mode: str | None = None
    categories: list[str] | None = None
