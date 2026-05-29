from difflib import SequenceMatcher

from src.core.types import ReviewResult, Finding

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class PostProcessor:
    def __init__(self, min_confidence: float = 0.5, max_findings: int = 20):
        self.min_confidence = min_confidence
        self.max_findings = max_findings

    def process(self, result: ReviewResult) -> ReviewResult:
        findings = result.findings
        warnings = list(result.warnings)

        # 1. Filter low confidence
        before = len(findings)
        findings = [f for f in findings if f.confidence >= self.min_confidence]
        if before > len(findings):
            warnings.append(
                f"Filtered {before - len(findings)} low-confidence findings "
                f"(< {self.min_confidence:.0%})"
            )

        # 2. Sort by severity first (so dedup keeps higher-severity findings)
        findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))

        # 3. Evidence gate: degrade findings without evidence
        no_evidence = 0
        for f in findings:
            if not f.evidence or not f.evidence.strip():
                f.confidence = max(0, f.confidence - 0.3)
                no_evidence += 1
        if no_evidence:
            warnings.append(
                f"Degraded {no_evidence} finding(s) without evidence (-0.3 confidence)"
            )

        # 4. Deduplicate
        findings = self._dedup(findings)

        # 5. Re-filter after evidence degradation
        before_evidence = len(findings)
        findings = [f for f in findings if f.confidence >= self.min_confidence]
        if before_evidence > len(findings):
            warnings.append(
                f"Filtered {before_evidence - len(findings)} finding(s) "
                f"after evidence gate"
            )

        # 6. Limit
        if len(findings) > self.max_findings:
            warnings.append(
                f"Truncated {len(findings) - self.max_findings} findings "
                f"(max {self.max_findings})"
            )
            findings = findings[:self.max_findings]

        return ReviewResult(
            summary=result.summary,
            findings=findings,
            metadata=result.metadata,
            warnings=warnings,
            errors=result.errors,
        )

    def _dedup(self, findings: list[Finding]) -> list[Finding]:
        kept: list[Finding] = []
        for f in findings:
            if not any(self._similar(f, k) for k in kept):
                kept.append(f)
        return kept

    def _similar(self, a: Finding, b: Finding) -> bool:
        if a.location.file != b.location.file:
            return False
        if a.category != b.category:
            return False
        # Titles are similar enough
        ratio = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
        return ratio > 0.8
