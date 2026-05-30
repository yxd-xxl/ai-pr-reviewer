"""Tests for multi-dimensional risk score."""

import pytest
from src.delivery.risk import RiskBreakdown, compute_risk_breakdown
from src.core.types import Finding, Location, ReviewResult, PullRequest, FileChange


def _finding(severity="high", category="security", confidence=0.9):
    return Finding(
        severity=severity, category=category,
        location=Location(file="app.py", line=10),
        title="Test", description="", suggestion="",
        confidence=confidence, evidence="code", analyzer="test",
    )


def _pr():
    return PullRequest(
        owner="o", repo="r", number=1, title="T", description="",
        url="https://github.com/o/r/pull/1",
        base_branch="main", head_branch="f", base_sha="a", head_sha="b",
    )


class TestRiskBreakdown:
    def test_defaults(self):
        rb = RiskBreakdown()
        assert rb.final_score == 0
        assert rb.level == "low"

    def test_score_clamped_to_100(self):
        rb = RiskBreakdown(base_score=120)
        assert rb.final_score <= 100

    def test_level_mapping(self):
        assert RiskBreakdown(base_score=10).level == "low"
        assert RiskBreakdown(base_score=25).level == "medium"
        assert RiskBreakdown(base_score=50).level == "high"
        assert RiskBreakdown(base_score=80).level == "critical"


class TestComputeRiskBreakdown:
    def test_empty_findings(self):
        result = ReviewResult(summary="", findings=[])
        rb = compute_risk_breakdown(result, _pr(), [])
        assert rb.final_score == 0
        assert rb.level == "low"

    def test_security_finding_increases_score(self):
        result = ReviewResult(summary="", findings=[
            _finding("critical", "security", 1.0)
        ])
        rb = compute_risk_breakdown(result, _pr(), [])
        assert rb.final_score > 30

    def test_multiple_findings_compound(self):
        result = ReviewResult(summary="", findings=[
            _finding("high", "security", 0.9),
            _finding("medium", "bug", 0.7),
        ])
        rb1 = compute_risk_breakdown(result, _pr(), [])
        rb_single = compute_risk_breakdown(
            ReviewResult(summary="", findings=[_finding("high", "security", 0.9)]),
            _pr(), [])
        assert rb1.final_score > rb_single.final_score

    def test_change_risk_detected(self):
        result = ReviewResult(summary="", findings=[])
        files = [FileChange(path="src/auth/login.py", status="modified",
                            language="python", diff="x", additions=5, deletions=2)]
        rb = compute_risk_breakdown(result, _pr(), files)
        assert rb.change_risk > 0

    def test_breakdown_has_component_fields(self):
        result = ReviewResult(summary="", findings=[_finding()])
        rb = compute_risk_breakdown(result, _pr(), [])
        # All breakdown components present
        assert isinstance(rb.base_score, int)
        assert isinstance(rb.security_penalty, int)
        assert isinstance(rb.change_risk, int)
        assert isinstance(rb.test_gap_penalty, int)

    def test_large_pr_increases_change_risk(self):
        result = ReviewResult(summary="", findings=[])
        small = [FileChange(path=f"file{i}.py", status="modified",
                            language="python", diff="x", additions=1, deletions=1)
                 for i in range(5)]
        large = [FileChange(path=f"file{i}.py", status="modified",
                            language="python", diff="x", additions=1, deletions=1)
                 for i in range(25)]
        rb_small = compute_risk_breakdown(result, _pr(), small)
        rb_large = compute_risk_breakdown(result, _pr(), large)
        assert rb_large.change_risk > rb_small.change_risk

    def test_low_severity_style_only_produces_low_risk(self):
        result = ReviewResult(summary="", findings=[
            _finding("low", "style", 0.5),
        ])
        rb = compute_risk_breakdown(result, _pr(), [])
        assert rb.level in ("low", "medium")
        assert rb.final_score < 40
