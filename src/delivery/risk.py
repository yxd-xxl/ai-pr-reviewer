"""Multi-dimensional risk score with breakdown — explainable, calibrated."""

from dataclasses import dataclass, field

from src.core.types import ReviewResult, PullRequest, FileChange

_SEVERITY_WEIGHT = {"critical": 60, "high": 30, "medium": 12, "low": 3}
_SECURITY_BONUS = {"security": 1.5, "bug": 1.0, "performance": 0.7,
                   "architecture": 0.5, "style": 0.3}

_SENSITIVE_PATTERNS = [
    "auth", "login", "session", "token", "password", "secret",
    "perm", "crypto", "key", "csrf", "oauth",
]


@dataclass
class RiskBreakdown:
    base_score: int = 0
    security_penalty: int = 0
    change_risk: int = 0
    test_gap_penalty: int = 0
    context_risk: int = 0
    evidence_bonus: int = 0

    @property
    def final_score(self) -> int:
        raw = (self.base_score + self.security_penalty + self.change_risk +
               self.test_gap_penalty + self.context_risk - self.evidence_bonus)
        return max(0, min(100, raw))

    @property
    def level(self) -> str:
        s = self.final_score
        if s < 15:
            return "low"
        elif s < 40:
            return "medium"
        elif s < 70:
            return "high"
        return "critical"


def compute_risk_breakdown(result: ReviewResult, pr: PullRequest,
                           files: list[FileChange]) -> RiskBreakdown:
    breakdown = RiskBreakdown()

    # 1. Base score: severity-weighted findings
    for f in result.findings:
        breakdown.base_score += int(
            _SEVERITY_WEIGHT.get(f.severity, 1) * min(f.confidence, 1.0))
    breakdown.base_score = min(100, breakdown.base_score)

    # 2. Security penalty: extra weight for security findings
    for f in result.findings:
        if f.category == "security" and f.severity in ("critical", "high"):
            breakdown.security_penalty += int(
                _SEVERITY_WEIGHT.get(f.severity, 1) * 0.5
            )
    breakdown.security_penalty = min(50, breakdown.security_penalty)

    # 3. Change risk: based on file count, size, and sensitive paths
    num_files = len(files)
    total_changes = sum(fc.additions + fc.deletions for fc in files)
    breakdown.change_risk = min(20, num_files // 5 + total_changes // 100)

    for fc in files:
        path_lower = fc.path.lower()
        for pattern in _SENSITIVE_PATTERNS:
            if pattern in path_lower:
                breakdown.change_risk += 5
                break
    breakdown.change_risk = min(40, breakdown.change_risk)

    # 4. Test gap: no test files changed alongside source changes
    source_files = [fc for fc in files
                    if not fc.path.startswith("test") and "test" not in fc.path.lower()]
    test_files = [fc for fc in files
                  if "test" in fc.path.lower() or fc.path.startswith("test")]
    if source_files and not test_files:
        breakdown.test_gap_penalty = min(10, len(source_files) * 2)

    # 5. Evidence bonus: discount risk if findings have SAST backing
    evidence_count = sum(1 for f in result.findings if f.evidence and f.evidence.strip())
    if result.findings:
        evidence_ratio = evidence_count / len(result.findings)
        breakdown.evidence_bonus = int(evidence_ratio * 10)

    return breakdown
