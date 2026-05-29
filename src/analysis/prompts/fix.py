_FIX_SYSTEM = """\
You are a code fix generator. Given a finding and the current code, output \
a unified diff that fixes the issue.

Output JSON only:
{
  "patch": "unified diff fixing the issue, or empty string if no fix needed",
  "explanation": "one sentence explaining the fix"
}

The patch must be a valid unified diff. If you cannot generate a safe fix, \
output an empty patch string. Do NOT generate fixes that could introduce \
new bugs or change behavior beyond fixing the reported issue."""

_FIX_USER = """\
Finding: {title}
Severity: {severity}
Category: {category}
Description: {description}
Suggested fix: {suggestion}

Current code:
```{language}
{code_snippet}
```

Generate a unified diff that fixes this specific issue. \
Output JSON."""  # noqa: E501


def build_fix_prompt(finding, code_snippet: str, language: str = "python") -> tuple[str, str]:
    user = _FIX_USER.format(
        title=finding.title,
        severity=finding.severity,
        category=finding.category,
        description=finding.description,
        suggestion=finding.suggestion,
        language=language,
        code_snippet=code_snippet[:3000],
    )
    return _FIX_SYSTEM, user
