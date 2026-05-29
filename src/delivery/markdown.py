from src.core.types import ReviewResult
from src.delivery.checklist import render_checklist_md


def render_markdown(result: ReviewResult) -> str:
    lines: list[str] = []
    lines.append("# AI PR Review Report")
    lines.append("")
    lines.append(result.summary)
    lines.append("")

    if result.findings:
        lines.append("---")
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        lines.append(f"| # | Severity | Category | File | Title | Confidence |")
        lines.append(f"|---|----------|----------|------|-------|------------|")
        for i, f in enumerate(result.findings, 1):
            loc = f"{f.location.file}"
            if f.location.line:
                loc += f":{f.location.line}"
            lines.append(
                f"| {i} | `{f.severity}` | `{f.category}` | {loc} | "
                f"{f.title} | {f.confidence:.0%} |"
            )
        lines.append("")

        for i, f in enumerate(result.findings, 1):
            lines.append(f"### {i}. {f.title}")
            lines.append("")
            lines.append(f"**Severity:** `{f.severity}` | **Category:** `{f.category}` | "
                         f"**Confidence:** {f.confidence:.0%}")
            lines.append("")
            lines.append(f"**File:** `{f.location.file}`" +
                         (f":{f.location.line}" if f.location.line else ""))
            lines.append("")
            lines.append(f"**Description:** {f.description}")
            lines.append("")
            if f.evidence:
                lines.append(f"**Evidence:** {f.evidence}")
                lines.append("")
            lines.append(f"**Suggestion:** {f.suggestion}")
            lines.append("")
    else:
        lines.append("No findings.")
        lines.append("")

    if result.warnings:
        lines.append("---")
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")

    if result.errors:
        lines.append("---")
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for e in result.errors:
            lines.append(f"- {e}")

    # Checklist
    lines.append(render_checklist_md(result))
    lines.append("")

    if result.metadata:
        lines.append("---")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append("```")
        for k, v in result.metadata.items():
            lines.append(f"{k}: {v}")
        lines.append("```")

    return "\n".join(lines)
