from src.core.types import FileChange, ReviewContext
from src.security.bandit_runner import BanditFinding
from src.langs.registry import get_lang


_ANALYSIS_SYSTEM = """\
You are a senior code reviewer. Analyze the diff through MULTIPLE PERSPECTIVES.
For each perspective below, check the code and report issues if found.
If no issues found in a perspective, move on — do NOT invent problems.

PERSPECTIVE 1 — Logic & Bugs:
  - Incorrect conditions, wrong data flow, race conditions
  - Null/undefined handling, boundary errors, off-by-one
  - Missing error handling, swallowed exceptions
  - Incorrect variable usage, naming confusion causing bugs

PERSPECTIVE 2 — Security:
  - Injection risks (SQL, command, path traversal)
  - Exposed secrets, hardcoded credentials
  - Missing auth checks, privilege escalation
  - Insecure deserialization (pickle, eval, yaml.load)

PERSPECTIVE 3 — Performance:
  - N+1 queries, unnecessary loops, blocking I/O
  - Memory leaks, large allocations in hot paths
  - Missing caching opportunities

PERSPECTIVE 4 — Quality & Tests:
  - Weak test assertions, missing edge case coverage
  - Unclear naming, misleading comments
  - Overly complex functions (should be split)

PERSPECTIVE 5 — Failure Modes:
  - What happens if this code fails? Is the error logged or silently swallowed?
  - Are there try/except blocks that catch too broadly (Exception, BaseException)?
  - If an external dependency (API, file, network) fails, does the user know?
  - Are return codes beyond 0/1 handled? Is stderr checked?

PERSPECTIVE 6 — Design Resilience:
  - Are values hardcoded that should be configurable (thresholds, limits, flags)?
  - Will this design choice cause problems when the system grows?
  - Is there a reasonable default that could be overridden?
  - Does the code make assumptions that may not hold in 6 months?

CRITICAL RULES:
- DO NOT comment on import statements or module existence.
- ONLY flag issues in NEW/ADDED code (lines starting with + in the diff).
  Ignore issues in removed code (lines starting with -) — those are being fixed.
- If the diff shows a bug being fixed, do NOT flag the old code as an issue.

Output format:
{
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "security|bug|performance|style|architecture",
      "classification": "new|preexisting|nit",
      "title": "short title",
      "description": "detailed description of the issue",
      "suggestion": "actionable fix suggestion",
      "line": <new-file-line-number-or-null>,
      "evidence": "copy-paste the exact code from the diff",
      "confidence": 0|25|50|75|100
    }
  ]
}

Confidence: 0=FP 25=maybe 50=real-minor 75=real-important 100=certain.
Confidence >= 50 required. Below 50, exclude.
classification: "new"=introduced by this PR, "preexisting"=was already in codebase, "nit"=trivial.
No issues → {"findings": []}"""

_ANALYSIS_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})

PR Context: {pr_title}

{content_label}:
{content}

Review the code above and output findings in JSON format."""


def build_analysis_prompt(fc: FileChange, ctx: ReviewContext,
                          bandit: list[BanditFinding] | None = None) -> tuple[str, str]:
    # Use full file content as primary review target (avoids diff confusion)
    if fc.full_content:
        content_label = "Current file content (review this)"
        content = fc.full_content[:6000]
        if len(fc.full_content) > 6000:
            content += "\n... (truncated)"
    else:
        content_label = "Diff"
        content = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"

    # Inject SAST findings as verification hints
    sast_section = ""
    if bandit:
        relevant = [b for b in bandit
                    if b.file == fc.path
                    or fc.path.endswith(b.file.split("/")[-1])]
        if relevant:
            lines = [
                "SAST (Bandit) detected the following in this file. "
                "Verify each — confirm if it's a real issue or a false positive:",
                "",
            ]
            for b in relevant:
                lines.append(
                    f"  [{b.issue_id}] {b.severity}/{b.confidence} "
                    f"Line {b.line}: {b.description}"
                )
            sast_section = "\n".join(lines)

    user = _ANALYSIS_USER.format(
        path=fc.path,
        language=fc.language or "unknown",
        status=fc.status,
        additions=fc.additions,
        deletions=fc.deletions,
        pr_title=ctx.pr.title,
        content_label=content_label,
        content=content,
    )

    # Inject language-specific hints
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"

    if sast_section:
        user += (
            f"\n\n{sast_section}\n\n"
            "For each SAST finding, confirm (REAL) or explain "
            "why it's a false positive (FP)."
        )
    return _ANALYSIS_SYSTEM, user
