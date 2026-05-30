"""Bug-focused analysis prompt — logic errors, state issues, failure modes."""

from src.core.types import FileChange, ReviewContext


_BUG_SYSTEM = """\
You are a senior software engineer specializing in bug detection. \
Analyze the code for LOGIC ERRORS and FAILURE MODES. \
Do NOT comment on security, performance, or style unless it causes a bug.

PERSPECTIVE 1 — Logic & Control Flow Bugs:
  - Incorrect conditions, wrong boolean logic, inverted comparisons
  - Wrong data flow, variable shadowing causing unexpected values
  - Race conditions, stale closures, mutable default arguments
  - Null/undefined handling, boundary errors, off-by-one
  - Missing error handling, swallowed exceptions, bare except
  - Incorrect variable usage, naming confusion causing bugs
  - Type confusion, implicit coercion causing wrong behavior

PERSPECTIVE 2 — State & Side Effects:
  - Shared mutable state modified unexpectedly
  - Missing copy/deepcopy causing aliasing bugs
  - Incorrect initialization order, partial state
  - State not cleaned up (resource leaks, stale entries)

PERSPECTIVE 3 — Failure Modes:
  - What happens if this code fails? Is the error logged or silently swallowed?
  - Are there try/except blocks that catch too broadly (Exception, BaseException)?
  - If an external dependency (API, file, network) fails, does the caller know?
  - Are return codes beyond 0/1 handled? Is stderr checked?
  - Does the code handle empty inputs, None, missing keys, timeouts?

CRITICAL RULES:
- DO NOT comment on import statements or module existence.
- ONLY flag issues in NEW/ADDED code (lines starting with + in the diff).
  Ignore issues in removed code (lines starting with -).
- If the diff shows a bug being fixed, do NOT flag the old code.

Output format:
{
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "bug",
      "title": "short title",
      "description": "detailed description of the bug",
      "suggestion": "actionable fix suggestion",
      "line": <new-file-line-number-or-null>,
      "evidence": "copy-paste the exact code from the diff",
      "classification": "new|preexisting|nit",
      "confidence": 0|25|50|75|100
    }
  ]
}

Confidence: 0=FP 25=maybe 50=real-minor 75=real-important 100=certain.
Confidence >= 50 required. No issues -> {"findings": []}."""


_BUG_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})

PR Context: {pr_title}

{content_label}:
{content}

Review the code above for bugs and failure modes. Output findings in JSON format."""


def build_bug_prompt(fc: FileChange, ctx: ReviewContext,
                     sast_findings: list | None = None) -> tuple[str, str]:
    if fc.full_content:
        content_label = "Current file content"
        content = fc.full_content[:6000]
        if len(fc.full_content) > 6000:
            content += "\n... (truncated)"
    else:
        content_label = "Diff"
        content = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"

    user = _BUG_USER.format(
        path=fc.path,
        language=fc.language or "unknown",
        status=fc.status,
        additions=fc.additions,
        deletions=fc.deletions,
        pr_title=ctx.pr.title,
        content_label=content_label,
        content=content,
    )

    # Inject SAST hints if available
    if sast_findings:
        relevant = []
        for b in sast_findings:
            b_file = getattr(b, 'file', '')
            if b_file == fc.path or fc.path.endswith(b_file.split("/")[-1]):
                relevant.append(b)
        if relevant:
            lines = ["SAST tools flagged these — verify each:", ""]
            for b in relevant:
                b_sev = getattr(b, 'severity', '?')
                lines.append(f"  [{b.issue_id}] {b_sev} Line {b.line}: {b.description}")
            user += "\n\n" + "\n".join(lines)
            user += "\n\nFor each SAST finding, confirm (REAL) or explain why FP."

    from src.langs.registry import get_lang
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"

    return _BUG_SYSTEM, user
