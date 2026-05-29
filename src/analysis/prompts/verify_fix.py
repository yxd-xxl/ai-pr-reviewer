_VERIFY_FIX_SYSTEM = """\
You are a code fix auditor. Your job is to independently verify whether \
a proposed code fix correctly resolves the reported issue without \
introducing new problems.

Output JSON only:
{
  "verified": true|false,
  "confidence": 0|25|50|75|100,
  "issues": "description of any problems, or empty string if clean",
  "suggestion": "how to improve the fix, or empty string if good"
}

Checks to perform:
1. Does the fix actually resolve the reported issue?
2. Does the fix change only what's necessary?
3. Could the fix introduce new bugs, side effects, or performance issues?
4. Is the fix idiomatic for the language?"""

_FIX_USER = """\
Original finding:
- Title: {title}
- Severity: {severity}
- Description: {description}
- Suggested approach: {suggestion}

Original code context:
```{language}
{original_code}
```

Proposed fix (unified diff):
```diff
{fix_patch}
```

Verify whether this fix is correct and safe. Output JSON."""  # noqa: E501


def build_verify_fix_prompt(finding, original_code: str,
                            language: str = "python") -> tuple[str, str]:
    user = _FIX_USER.format(
        title=finding.title,
        severity=finding.severity,
        description=finding.description,
        suggestion=finding.suggestion,
        language=language,
        original_code=original_code[:2000],
        fix_patch=finding.fix_patch or "(none)",
    )
    return _VERIFY_FIX_SYSTEM, user
