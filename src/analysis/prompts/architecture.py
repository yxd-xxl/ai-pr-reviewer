"""Architecture analysis prompt — module boundaries, dependency direction, design resilience."""

from src.core.types import FileChange, ReviewContext

_ARCH_SYSTEM = """\
You are a software architect. Analyze the code for ARCHITECTURE and DESIGN issues.
Do NOT flag bugs, security, performance, or style unless it's architectural.

FOCUS AREAS:
1. Module Boundaries:
   - Feature A importing internal modules from Feature B (layering violation)
   - Circular dependencies between modules
   - Violation of declared architecture rules

2. Dependency Direction:
   - Low-level module depending on high-level module (dependency inversion)
   - core/ importing from context/ or delivery/ (inner depending on outer)
   - Missing abstraction layer forcing direct coupling

3. Duplication & Abstraction:
   - Same logic implemented in 2+ places (should be extracted to shared/common)
   - Missing interface/ABC causing tight coupling to concrete implementation
   - Config values that should be parameterized

4. Design Resilience:
   - Hardcoded values (thresholds, limits, URLs, flags) that should be configurable
   - Magic numbers without named constants
   - Assumptions that may not hold in 6 months (scalability, extensibility)

CRITICAL RULES:
- DO NOT comment on import statements unless it reveals a boundary violation.
- ONLY flag issues in NEW/ADDED code (lines starting with +).
- No issues -> {"findings": []}
- Confidence >= 40 required (architecture issues are judgment-based).

Output JSON:
{"findings": [{"severity": "critical|high|medium|low", "category": "architecture",
  "title": "...", "description": "...", "suggestion": "...", "line": <int|null>,
  "evidence": "...", "classification": "new|preexisting|nit", "confidence": 0|25|50|75|100}]}"""

_ARCH_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})
PR Context: {pr_title}

{content_label}:
{content}

{conventions_section}
Review for architecture and design issues. Output JSON."""


def build_architecture_prompt(fc: FileChange, ctx: ReviewContext,
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
        conv_lines = ["Architecture constraints (from project conventions):", ""]
        for c in ctx.conventions:
            conv_lines.append(f"From {c.source} ({c.type}):")
            conv_lines.append(c.content[:1000])
            conv_lines.append("")
        conventions_section = "\n".join(conv_lines)

    user = _ARCH_USER.format(
        path=fc.path, language=fc.language or "unknown",
        status=fc.status, additions=fc.additions, deletions=fc.deletions,
        pr_title=ctx.pr.title, content_label=content_label, content=content,
        conventions_section=conventions_section,
    )
    from src.langs.registry import get_lang
    lang = get_lang(fc.language)
    if lang and lang.prompt_hints:
        user += f"\n\n{lang.prompt_hints}"
    return _ARCH_SYSTEM, user
