from src.core.types import FileChange, ReviewContext


_SECURITY_SYSTEM = """\
You are a senior application security engineer performing a security-focused \
code review. Identify vulnerabilities according to OWASP Top 10 and CWE.

CRITICAL: DO NOT comment on import statements or module existence.

Focus on:
- SQL Injection / Command Injection
- Cross-Site Scripting (XSS)
- Sensitive Data Exposure / Hardcoded Secrets
- Broken Access Control
- Insecure Deserialization (pickle, yaml.unsafe_load)
- Path Traversal
- Server-Side Request Forgery (SSRF)
- Missing Input Validation
- Weak Cryptography

For each finding, classify with a CWE ID when applicable.
Output valid JSON only:

{
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "security",
      "cwe_id": "CWE-89 or null",
      "title": "short title",
      "description": "detailed description",
      "suggestion": "actionable fix",
      "line": <line-number-or-null>,
      "evidence": "copy-paste the vulnerable code",
      "classification": "new|preexisting|nit",
      "confidence": 0|25|50|75|100
    }
  ]
}

Confidence: 0=FP 25=maybe 50=real-minor 75=real-important 100=certain.
Confidence >= 50 required. No issues → {"findings": []}"""

_ANALYSIS_USER = """\
File: {path} ({language})
Status: {status} (+{additions}/-{deletions})

PR Context: {pr_title}

Diff:
{diff}

Analyze the diff above and output findings in JSON format."""


def build_security_prompt(fc: FileChange, ctx: ReviewContext,
                          sast_findings: list | None = None) -> tuple[str, str]:
    diff = fc.diff if len(fc.diff) < 8000 else fc.diff[:8000] + "\n... (truncated)"
    user = _ANALYSIS_USER.format(
        path=fc.path,
        language=fc.language or "unknown",
        status=fc.status,
        additions=fc.additions,
        deletions=fc.deletions,
        pr_title=ctx.pr.title,
        diff=diff,
    )
    if sast_findings:
        relevant = []
        for b in sast_findings:
            b_file = getattr(b, 'file', '')
            if b_file == fc.path:
                relevant.append(b)
        if relevant:
            lines = ["SAST tools flagged these — verify each:", ""]
            for b in relevant:
                lines.append(f"  [{b.issue_id}] Line {b.line}: {b.description}")
            user += "\n\n" + "\n".join(lines)
    return _SECURITY_SYSTEM, user
