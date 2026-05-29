from src.core.types import ReviewResult, Finding

_SEVERITY_WEIGHTS = {
    "critical": 60,
    "high": 30,
    "medium": 12,
    "low": 3,
}

_URGENCY_ORDER = {"critical": 1, "high": 2, "medium": 3, "low": 4}


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

def action_plan(result: ReviewResult) -> list[str]:
    """Generate priority-ordered action plan from findings."""
    sorted_findings = sorted(
        result.findings,
        key=lambda f: (_URGENCY_ORDER.get(f.severity, 99), -(f.confidence or 0))
    )
    lines = ["", "## Action Plan", ""]
    current_urgency = None
    labels = {1: "Blocking", 2: "Should Fix", 3: "Consider", 4: "Optional"}
    for f in sorted_findings:
        u = _URGENCY_ORDER.get(f.severity, 99)
        if u != current_urgency:
            current_urgency = u
            lines.append(f"### {labels.get(u, 'Other')}")
        lines.append(f"- [ ] [{f.severity.upper()}] {f.title}")
        if f.fix_patch:
            lines.append(f"  - Fix available: `fix patch generated`")
    return lines
