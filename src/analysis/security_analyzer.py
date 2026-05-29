from src.core.types import ReviewContext, ReviewResult, Finding, Location
from src.analysis.analyzer import Analyzer
from src.analysis.confidence import parse_confidence
from src.analysis.prompts import build_security_prompt, build_summary_prompt
from src.llm import LLMAdapter
from src.security.bandit_runner import run_bandit


class SecurityAnalyzer(Analyzer):
    """Security-focused analyzer with CWE classification."""

    def __init__(self, adapter: LLMAdapter):
        self._adapter = adapter

    def analyze(self, context: ReviewContext) -> ReviewResult:
        warnings: list[str] = []
        errors: list[str] = []
        findings: list[Finding] = []

        # SAST pre-filter
        file_paths = [f.path for f in context.files]
        bandit_findings, bandit_warnings = run_bandit(file_paths)
        warnings.extend(bandit_warnings)
        if bandit_findings:
            warnings.append(
                f"Bandit SAST: {len(bandit_findings)} finding(s)"
            )

        # Summary
        summary = self._generate_summary(context, warnings, errors)

        # Per-file security analysis
        for fc in context.files:
            if fc.is_binary or fc.status == "removed":
                continue
            try:
                system, user = build_security_prompt(fc, context, bandit_findings)
                data = self._adapter.complete_json(system=system, user=user)
                for f in data.get("findings", []):
                    if parse_confidence(f.get("confidence", 50)) >= 0.5:
                        findings.append(Finding(
                            severity=f.get("severity", "medium"),
                            category="security",
                            location=Location(file=fc.path, line=f.get("line"), side="RIGHT"),
                            title=f.get("title", ""),
                            description=f.get("description", ""),
                            suggestion=f.get("suggestion", ""),
                            classification=f.get("classification", "new"),
                            confidence=parse_confidence(f.get("confidence", 50)),
                            evidence=f.get("evidence"),
                            rule_id=f.get("cwe_id"),
                            analyzer="security",
                        ))
            except Exception as e:
                errors.append(f"Security analysis failed for {fc.path}: {e}")

        return ReviewResult(
            summary=summary, findings=findings,
            metadata={"analyzer": "security", "model": "llm"},
            warnings=warnings, errors=errors,
        )

    def _generate_summary(self, ctx, warnings, errors):
        try:
            system, user = build_summary_prompt(ctx)
            return self._adapter.complete(system=system, user=user).content
        except Exception as e:
            errors.append(f"Summary failed: {e}")
            return f"## Security Review\n\nFailed: {e}"
