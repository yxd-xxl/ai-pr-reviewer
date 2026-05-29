_VERIFY_SYSTEM = """\
You are a code review auditor. Your job is to independently verify whether \
a finding reported by another reviewer is a real issue.

Output JSON only:
{
  "verified": true|false,
  "confidence": 0|25|50|75|100,
  "reason": "one sentence explaining your judgment"
}

Only mark verified=true if you are confident (>=50) the issue is real and \
actionable. False positives, style nits that linters catch, and vague claims \
should be verified=false."""

_VERIFY_USER = """\
Review a finding reported for this code change:

File: {path}
Category: {category}
Severity: {severity}
Finding: {title}
Description: {description}
Evidence cited: {evidence}

Diff context:
{diff}

Is this finding a real, actionable issue? Output JSON."""


def build_verify_prompt(finding, fc, diff_snippet: str = "") -> tuple[str, str]:
    user = _VERIFY_USER.format(
        path=fc.path,
        category=finding.category,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        evidence=finding.evidence or "(none)",
        diff=diff_snippet or fc.diff[:2000],
    )
    return _VERIFY_SYSTEM, user
