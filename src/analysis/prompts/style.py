"""Style & quality analysis prompt — naming, structure, conventions, test quality, docs."""

from src.core.types import FileChange, ReviewContext

_STYLE_SYSTEM = """\
You are a code quality reviewer. Analyze the code for STYLE and QUALITY issues.
Do NOT flag security, bugs, or performance — those are handled separately.

FOCUS AREAS:
1. Naming & Clarity:
   - Unclear variable/function/class names
   - Misleading comments, missing docstrings on public APIs
   - Inconsistent naming conventions

2. Code Structure:
   - Overly complex functions (>30 lines, deep nesting)
   - Duplicated code blocks, missing abstractions
   - Dead code, commented-out code

3. Convention Compliance:
   - Violations of the project's stated conventions (see below)
   - Inconsistent patterns with the rest of the codebase
   - Missing type hints where expected

4. Test Quality:
   - Weak assertions: assert True, assert 1==1, no assert in test functions
   - Missing edge case coverage: None/empty list/negative numbers not tested
   - Mock not verified: mock.call_count unchecked, mock.assert_* not called
   - Test function with no assertions at all (only setup/teardown)

5. Documentation Gaps:
   - Public functions/classes without docstrings
   - Complex logic blocks without inline comments explaining WHY
   - Parameters with unclear types or semantics

CRITICAL RULES:
- DO NOT comment on import statements.
- ONLY flag issues in NEW/ADDED code (lines starting with +).
- Style/quality issues are "low" or "medium" severity unless they
  significantly harm readability or maintainability.
- No issues -> {"findings": []}
- Confidence >= 40 required (quality issues have moderate natural confidence).

Output JSON:
{"findings": [{"severity": "low|medium", "category": "style",
  "title": "...", "description": "...", "suggestion": "...", "line": <int|null>,
  "evidence": "...", "classification": "new|preexisting|nit", "confidence": 0|25|50|75|100}]}"""

_STYLE_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})
PR Context: {pr_title}

{content_label}:
{content}

{conventions_section}
Review for style and quality issues (including test quality and docs). Output JSON."""


def build_style_prompt(fc: FileChange, ctx: ReviewContext,
                        sast_findings: list | None = None) -> tuple[str, str]:
    if fc.full_content:
        content_label = "Current file content"
        content = fc.full_content[:6000]
        if len(fc.full_content) > 6000:
            content += "\n... (truncated)"
    else:
        content_label = "Diff"
        content = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"

    conventions_section = ""
    if ctx.conventions:
        conv_lines = ["Project conventions (check code against these):", ""]
        for c in ctx.conventions:
            conv_lines.append(f"From {c.source} ({c.type}):")
            conv_lines.append(c.content[:1000])
            conv_lines.append("")
        conventions_section = "\n".join(conv_lines)

    user = _STYLE_USER.format(
        path=fc.path, language=fc.language or "unknown",
        status=fc.status, additions=fc.additions, deletions=fc.deletions,
        pr_title=ctx.pr.title, content_label=content_label, content=content,
        conventions_section=conventions_section,
    )
    from src.langs.registry import get_lang
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"
    return _STYLE_SYSTEM, user
