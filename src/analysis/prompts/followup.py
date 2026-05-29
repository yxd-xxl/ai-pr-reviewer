_FOLLOWUP_SYSTEM = """\
You are a code review assistant. A finding was reported during code review \
and the developer has a follow-up question. Answer based on the code context.

Output JSON only:
{
  "answer": "clear answer to the question",
  "is_valid_concern": true|false,
  "alternative_fixes": ["alternative 1", "alternative 2"]
}

If the finding appears to be a false positive, set is_valid_concern=false \
and explain why."""

_FOLLOWUP_USER = """\
Finding: {title}
Severity: {severity}
Category: {category}
Description: {description}
Evidence: {evidence}
Suggested fix: {suggestion}

Code context:
```{language}
{code_snippet}
```

Question: {question}

Answer the question and output JSON."""  # noqa: E501


def build_followup_prompt(finding, code_snippet: str, question: str,
                          language: str = "python") -> tuple[str, str]:
    user = _FOLLOWUP_USER.format(
        title=finding.title,
        severity=finding.severity,
        category=finding.category,
        description=finding.description,
        evidence=finding.evidence or "(none)",
        suggestion=finding.suggestion or "(none)",
        language=language,
        code_snippet=code_snippet[:3000],
        question=question,
    )
    return _FOLLOWUP_SYSTEM, user
