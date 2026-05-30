"""Failure modes analysis prompt — exceptions, external deps, resource lifecycle."""

from src.core.types import FileChange, ReviewContext

_FAILURE_SYSTEM = """\
You are a reliability engineer. Analyze the code for FAILURE MODES and ROBUSTNESS issues.
Do NOT comment on security, performance, or style unless it causes a failure.

PERSPECTIVE 1 — Exception & Error Handling:
  - Bare except: catching Exception or BaseException, swallowing errors silently
  - pass/print in except blocks instead of logging or re-raising
  - Missing finally block causing resource leaks (file/socket/connection not closed)
  - except block that catches errors it cannot handle
  - Re-raising without preserving original traceback

PERSPECTIVE 2 — External Dependency Failures:
  - API/DB/network calls without timeout handling
  - No retry logic or exponential backoff on transient failures
  - No fallback/default when external service is unavailable
  - stderr from subprocess not checked, return codes beyond 0/1 ignored
  - File I/O without checking existence/permissions

PERSPECTIVE 3 — Resource Lifecycle:
  - Files opened without context manager (with open) or explicit close
  - Socket/connection opened but close not guaranteed (missing finally/context manager)
  - Resources created in loop body without cleanup
  - Thread/process pool not shut down, leading to resource exhaustion

CRITICAL RULES:
- DO NOT comment on import statements.
- ONLY flag issues in NEW/ADDED code (lines starting with +).
- No issues -> {"findings": []}
- Confidence >= 40 required (failure modes often have lower natural confidence than bugs).

Output JSON:
{"findings": [{"severity": "critical|high|medium|low", "category": "failure",
  "title": "...", "description": "...", "suggestion": "...", "line": <int|null>,
  "evidence": "...", "classification": "new|preexisting|nit", "confidence": 0|25|50|75|100}]}"""

_FAILURE_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})
PR Context: {pr_title}

{content_label}:
{content}

Review for failure modes and robustness issues. Output JSON."""


def build_failure_prompt(fc: FileChange, ctx: ReviewContext,
                         sast_findings: list | None = None) -> tuple[str, str]:
    if fc.full_content:
        content_label = "Current file content"
        content = fc.full_content[:6000]
        if len(fc.full_content) > 6000:
            content += "\n... (truncated)"
    else:
        content_label = "Diff"
        content = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"

    user = _FAILURE_USER.format(
        path=fc.path, language=fc.language or "unknown",
        status=fc.status, additions=fc.additions, deletions=fc.deletions,
        pr_title=ctx.pr.title, content_label=content_label, content=content,
    )
    from src.langs.registry import get_lang
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"
    return _FAILURE_SYSTEM, user
