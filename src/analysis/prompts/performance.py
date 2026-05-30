"""Performance-focused analysis prompt."""

from src.core.types import FileChange, ReviewContext

_PERF_SYSTEM = """\
You are a senior performance engineer. Analyze the code for PERFORMANCE ISSUES.
Do NOT comment on security, style, or architecture unless it causes a performance problem.

FOCUS AREAS:
1. Algorithmic Complexity:
   - O(n^2) or worse where O(n log n) or O(n) is possible
   - Unnecessary nested loops, redundant iterations

2. I/O & Blocking:
   - N+1 database queries, repeated API calls in loops
   - Blocking I/O in async contexts, missing caching
   - Large file reads without streaming

3. Memory:
   - Memory leaks, unbounded collections, missing cleanup
   - Large allocations in hot paths, unnecessary copies
   - Unclosed resources (files, connections, sessions)

4. Concurrency:
   - Missed parallelization opportunities
   - Unnecessary serialization, lock contention

CRITICAL RULES:
- DO NOT comment on import statements.
- ONLY flag issues in NEW/ADDED code (lines starting with +).
- No issues -> {"findings": []}
- Confidence >= 50 required.

Output JSON:
{"findings": [{"severity": "critical|high|medium|low", "category": "performance",
  "title": "...", "description": "...", "suggestion": "...", "line": <int|null>,
  "evidence": "...", "classification": "new|preexisting|nit", "confidence": 0|25|50|75|100}]}"""

_PERF_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})
PR Context: {pr_title}

{content_label}:
{content}

Review for performance issues. Output JSON."""


def build_performance_prompt(fc: FileChange, ctx: ReviewContext,
                              sast_findings: list | None = None) -> tuple[str, str]:
    if fc.full_content:
        content_label = "Current file content"
        content = fc.full_content[:6000]
        if len(fc.full_content) > 6000:
            content += "\n... (truncated)"
    else:
        content_label = "Diff"
        content = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"

    user = _PERF_USER.format(
        path=fc.path, language=fc.language or "unknown",
        status=fc.status, additions=fc.additions, deletions=fc.deletions,
        pr_title=ctx.pr.title, content_label=content_label, content=content,
    )
    from src.langs.registry import get_lang
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"
    return _PERF_SYSTEM, user
