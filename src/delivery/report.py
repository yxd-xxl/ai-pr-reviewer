"""Comprehensive 9-section review report — coverage, breakdown, action priority."""

from src.core.types import ReviewResult, PullRequest, FileChange


def render_full_report(result: ReviewResult, pr: PullRequest,
                       files: list[FileChange],
                       coverage: dict | None = None) -> str:
    sections = [
        _render_overview(pr, files, result),
        _render_risk_summary(result, files),
        _render_coverage(files, result, coverage or {}),
        _render_findings_by_priority(result),
        _render_finding_details(result),
        _render_test_impact(files),
        _render_checklist(result),
        _render_delivery_log(result),
        _render_limitations(files, result),
    ]
    return "\n\n---\n\n".join(sections)


def _render_overview(pr, files, result) -> str:
    t = result.metadata.get("timing", {})
    return (
        f"# PR Review Report\n\n"
        f"**PR:** [{pr.title}]({pr.url})\n"
        f"**Author:** {pr.author or 'unknown'} | "
        f"**Branch:** {pr.head_branch} → {pr.base_branch}\n"
        f"**Files:** {len(files)} changed | "
        f"**Mode:** {result.metadata.get('analyzer', 'unknown')}\n"
        f"**Timing:** fetch={t.get('fetch','?')}s "
        f"analyze={t.get('analyze','?')}s "
        f"total={t.get('total','?')}s\n\n"
        f"## Summary\n\n{result.summary}"
    )


def _render_risk_summary(result, files) -> str:
    from src.delivery.checklist import risk_score as calc_risk
    score = calc_risk(result)
    if score < 15:
        level, suggestion = "LOW", "Safe to merge."
    elif score < 40:
        level, suggestion = "MEDIUM", "Review recommended before merge."
    elif score < 70:
        level, suggestion = "HIGH", "Address critical/high findings before merge."
    else:
        level, suggestion = "CRITICAL", "Do not merge until critical issues are resolved."

    sev_counts = {}
    for f in result.findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    lines = [
        "## Risk Summary",
        f"**Risk Score:** {score}/100 ({level})",
        f"**Recommendation:** {suggestion}",
        "",
        "### Severity Distribution",
    ]
    for sev in ("critical", "high", "medium", "low"):
        count = sev_counts.get(sev, 0)
        if count:
            lines.append(f"- **{sev.upper()}:** {count} finding(s)")
    if not sev_counts:
        lines.append("- No findings.")
    return "\n".join(lines)


def _render_coverage(files, result, coverage) -> str:
    analyzed = len([f for f in files if not f.is_binary and f.status != "removed"])
    skipped = len(files) - analyzed
    langs = set(f.language for f in files if f.language)

    lines = [
        "## Analysis Coverage",
        f"**Files changed:** {len(files)}",
        f"**Analyzed:** {analyzed}",
        f"**Skipped:** {skipped}",
    ]
    if skipped:
        skipped_files = [f.path for f in files
                        if f.is_binary or f.status == "removed"]
        for sf in skipped_files[:10]:
            lines.append(f"  - `{sf}`")
    lines.append(f"**Languages:** {', '.join(sorted(langs)) if langs else 'none'}")
    lines.append(f"**Findings total:** {len(result.findings)}")
    if result.warnings:
        lines.append(f"**Warnings:** {len(result.warnings)}")
    if result.errors:
        lines.append(f"**Errors:** {len(result.errors)}")
    return "\n".join(lines)


def _render_findings_by_priority(result) -> str:
    blocking = [f for f in result.findings if f.severity == "critical"]
    should_fix = [f for f in result.findings if f.severity == "high"]
    review = [f for f in result.findings if f.severity == "medium"]
    suggestions = [f for f in result.findings if f.severity == "low"]

    lines = ["## Findings by Priority"]
    for label, items in [("Blocking", blocking), ("Should Fix", should_fix),
                          ("Needs Review", review), ("Suggestions", suggestions)]:
        if items:
            lines.append(f"\n### {label} ({len(items)})")
            for f in items:
                lines.append(f"- **[{f.severity.upper()}]** {f.title} "
                           f"(`{f.location.file}`"
                           + (f":{f.location.line}" if f.location.line else "")
                           + ")")
    if not result.findings:
        lines.append("\nNo findings.")
    return "\n".join(lines)


def _render_finding_details(result) -> str:
    if not result.findings:
        return "## Finding Details\n\nNo findings."
    lines = ["## Finding Details"]
    for i, f in enumerate(result.findings, 1):
        lines.append(f"\n### {i}. {f.title}")
        lines.append(f"**Severity:** `{f.severity}` | **Category:** `{f.category}` | "
                    f"**Confidence:** {f.confidence:.0%} | **Analyzer:** {f.analyzer or '?'}")
        lines.append(f"**Location:** `{f.location.file}`"
                    + (f":{f.location.line}" if f.location.line else ""))
        lines.append(f"\n{f.description}")
        if f.evidence:
            lines.append(f"\n**Evidence:**\n```\n{f.evidence}\n```")
        lines.append(f"\n**Suggestion:** {f.suggestion}")
        if f.fix_patch:
            lines.append(f"\n**Fix Patch:** ```diff\n{f.fix_patch}\n```")
            lines.append(f"**Fix Verified:** {f.fix_verified}")
    return "\n".join(lines)


def _render_test_impact(files) -> str:
    test_files = [f for f in files if "test" in f.path.lower()]
    has_tests = len(test_files) > 0
    lines = ["## Test Impact"]
    if has_tests:
        lines.append(f"**{len(test_files)} test file(s)** modified:")
        for tf in test_files:
            lines.append(f"  - `{tf.path}`")
    else:
        lines.append("No test files modified in this PR.")
        lines.append("Consider adding tests for the changes above.")
    return "\n".join(lines)


def _render_checklist(result) -> str:
    from src.delivery.checklist import render_checklist_md
    return render_checklist_md(result)


def _render_delivery_log(result) -> str:
    lines = ["## Delivery Log"]
    lines.append(f"Findings delivered: {len(result.findings)}")
    if result.warnings:
        lines.append(f"Warnings: {len(result.warnings)}")
        for w in result.warnings[:5]:
            lines.append(f"  - {w}")
    return "\n".join(lines)


def _render_limitations(files, result) -> str:
    lines = ["## Limitations"]
    lines.append("- AI-generated review — findings may include false positives.")
    lines.append("- Review confidence is model-estimated, not calibrated probability.")
    large_files = [f for f in files if len(f.diff) > 8000]
    if large_files:
        lines.append(f"- {len(large_files)} file(s) had truncated diff analysis.")
    no_sast = [f for f in files if f.language not in ("python",)]
    if no_sast:
        langs = set(f.language for f in no_sast if f.language)
        if langs:
            lines.append(f"- SAST coverage limited for: {', '.join(langs)}.")
    return "\n".join(lines)
