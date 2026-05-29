from src.core.types import ReviewResult

_SEVERITY_WEIGHTS = {
    "critical": 60,
    "high": 30,
    "medium": 12,
    "low": 3,
}


def risk_score(result: ReviewResult) -> int:
    """Calculate risk score (0-100) from findings."""
    if not result.findings:
        return 0
    score = sum(
        _SEVERITY_WEIGHTS.get(f.severity, 1) * min(f.confidence, 1.0)
        for f in result.findings
    )
    return min(100, int(score))


def generate_checklist(result: ReviewResult) -> list[str]:
    """Generate reviewer checklist from findings."""
    items: list[str] = []
    by_category: dict[str, list] = {}
    for f in result.findings:
        by_category.setdefault(f.category, []).append(f)

    for cat, findings in sorted(by_category.items()):
        items.append(f"### {cat.title()}")
        for f in findings:
            items.append(
                f"- [ ] **[{f.severity.upper()}]** {f.title} "
                f"(`{f.location.file}`"
                + (f":{f.location.line}" if f.location.line else "")
                + ")"
            )
        items.append("")
    return items


def render_checklist_md(result: ReviewResult) -> str:
    """Render full checklist section in Markdown."""
    score = risk_score(result)

    label = (
        "LOW RISK" if score < 15
        else "MEDIUM RISK" if score < 40
        else "HIGH RISK" if score < 70
        else "CRITICAL RISK"
    )

    lines = [
        "## Review Checklist",
        "",
        f"**Risk Score:** {score}/100 ({label})",
        "",
    ]

    lines.extend(generate_checklist(result))
    return "\n".join(lines)
