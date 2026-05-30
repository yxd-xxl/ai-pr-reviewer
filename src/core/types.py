from dataclasses import dataclass, field
from enum import Enum


class FindingState(str, Enum):
    DETECTED = "detected"
    VERIFIED = "verified"
    PUBLISHED = "published"
    ACKNOWLEDGED = "acknowledged"
    MARKED_FP = "marked_fp"
    ACCEPTED = "accepted"
    FIXED = "fixed"
    DISMISSED = "dismissed"
    REOPENED = "reopened"


# ── PR ──────────────────────────────────────────

@dataclass
class PullRequest:
    owner: str
    repo: str
    number: int
    title: str
    description: str
    url: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str
    author: str | None = None


# ── Diff ────────────────────────────────────────

@dataclass
class DiffHunk:
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    content: str


@dataclass
class FileChange:
    path: str
    status: str          # added | modified | removed | renamed
    language: str
    diff: str
    hunks: list[DiffHunk] = field(default_factory=list)
    old_path: str | None = None
    is_binary: bool = False
    additions: int = 0
    deletions: int = 0
    full_content: str | None = None  # full file content for context


# ── Context ─────────────────────────────────────

@dataclass
class ProjectConvention:
    source: str          # .claude/CLAUDE.md, pyproject.toml, etc.
    type: str            # coding_style | architecture | test_policy | dependency
    content: str


@dataclass
class ReviewContext:
    pr: PullRequest
    files: list[FileChange]
    conventions: list[ProjectConvention] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── Findings ────────────────────────────────────

@dataclass
class Location:
    file: str
    line: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    side: str = "RIGHT"   # RIGHT = new code, LEFT = old code


@dataclass
class Finding:
    severity: str         # critical | high | medium | low
    category: str         # security | bug | performance | style | architecture
    location: Location
    title: str
    description: str
    suggestion: str
    confidence: float     # 0.0 ~ 1.0 (prompt uses 0/25/50/75/100)
    classification: str = "new"  # new | preexisting | nit
    evidence: str | None = None
    fix_patch: str | None = None
    fix_verified: bool = False
    fix_verification_note: str | None = None
    rule_id: str | None = None
    analyzer: str | None = None
    lifecycle_state: str = "detected"
    lifecycle_history: list = field(default_factory=list)


@dataclass
class FindingEvent:
    finding_fingerprint: str
    from_state: str
    to_state: str
    user: str = "system"
    reason: str = ""
    timestamp: str = ""


# ── Fix ─────────────────────────────────────────

@dataclass
class FixProposal:
    finding_fingerprint: str
    patch: str
    description: str
    status: str = "generated"  # generated|apply_failed|applied|test_failed|verified|rejected
    verification_note: str | None = None
    test_result: str | None = None
    risk_note: str = ""
    created_at: str = ""


@dataclass
class FixRun:
    pr_url: str
    proposals: list[FixProposal] = field(default_factory=list)
    status: str = "dry_run"
    branch: str = ""
    fix_pr_url: str = ""
    actions: list[str] = field(default_factory=list)


# ── Result ──────────────────────────────────────

@dataclass
class ReviewResult:
    summary: str
    findings: list[Finding]
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
