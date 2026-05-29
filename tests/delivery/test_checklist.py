import pytest
from src.delivery.checklist import generate_checklist, risk_score
from src.core.types import ReviewResult, Finding, Location


class TestRiskScore:
    def test_no_findings_zero_risk(self):
        result = ReviewResult(summary="", findings=[])
        assert risk_score(result) == 0

    def test_critical_finding_high_risk(self):
        result = ReviewResult(summary="", findings=[
            Finding(severity="critical", category="security",
                    location=Location(file="a.py"),
                    title="SQL injection", description="", suggestion="",
                    confidence=0.9),
        ])
        assert risk_score(result) > 50

    def test_only_low_severity(self):
        result = ReviewResult(summary="", findings=[
            Finding(severity="low", category="style",
                    location=Location(file="a.py"),
                    title="Naming", description="", suggestion="",
                    confidence=0.5),
        ])
        assert risk_score(result) < 20


class TestChecklist:
    def test_generates_items_per_category(self):
        result = ReviewResult(summary="", findings=[
            Finding(severity="critical", category="security",
                    location=Location(file="a.py"),
                    title="SQL injection", description="d", suggestion="s",
                    confidence=0.9),
            Finding(severity="medium", category="bug",
                    location=Location(file="b.py"),
                    title="Null check", description="d", suggestion="s",
                    confidence=0.8),
        ])
        items = generate_checklist(result)
        assert len(items) >= 2
        assert any("[ ]" in item for item in items)

    def test_empty_findings(self):
        result = ReviewResult(summary="", findings=[])
        items = generate_checklist(result)
        assert len(items) == 0
