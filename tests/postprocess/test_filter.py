import pytest
from src.postprocess.filter import PostProcessor
from src.core.types import ReviewResult, Finding, Location


def make_finding(severity="medium", category="style", title="Test",
                 file="a.py", line=1, confidence=0.8):
    return Finding(
        severity=severity, category=category, title=title,
        location=Location(file=file, line=line),
        description="", suggestion="", confidence=confidence,
    )


class TestPostProcessor:
    def test_filters_low_confidence(self):
        findings = [
            make_finding(title="Bug A", file="a.py", confidence=0.9),
            make_finding(title="Bug B", file="b.py", confidence=0.3),
            make_finding(title="Bug C", file="c.py", confidence=0.8),
        ]
        result = ReviewResult(summary="", findings=findings)
        pp = PostProcessor(min_confidence=0.5)
        filtered = pp.process(result)
        assert len(filtered.findings) == 2

    def test_deduplicates_similar_findings(self):
        findings = [
            make_finding(title="Null pointer risk", file="a.py", category="bug"),
            make_finding(title="Null pointer risk in auth", file="a.py", category="bug"),
            make_finding(title="Style improvement", file="b.py", category="style"),
        ]
        result = ReviewResult(summary="", findings=findings)
        pp = PostProcessor()
        filtered = pp.process(result)
        # Dedup should merge the two similar bug findings into 1 + style = 2
        assert len(filtered.findings) == 2

    def test_sorts_by_severity(self):
        findings = [
            make_finding(title="A", severity="low"),
            make_finding(title="B", severity="critical"),
            make_finding(title="C", severity="medium"),
        ]
        result = ReviewResult(summary="", findings=findings)
        pp = PostProcessor()
        filtered = pp.process(result)
        severities = [f.severity for f in filtered.findings]
        assert severities == ["critical", "medium", "low"]

    def test_limits_total_findings(self):
        findings = [make_finding(title=f"Issue {i}") for i in range(30)]
        result = ReviewResult(summary="", findings=findings)
        pp = PostProcessor(max_findings=10)
        filtered = pp.process(result)
        assert len(filtered.findings) <= 10

    def test_preserves_warnings_and_errors(self):
        result = ReviewResult(summary="", findings=[],
                              warnings=["w1"], errors=["e1"])
        pp = PostProcessor()
        filtered = pp.process(result)
        assert "w1" in filtered.warnings
        assert "e1" in filtered.errors

    def test_empty_findings(self):
        result = ReviewResult(summary="", findings=[])
        pp = PostProcessor()
        filtered = pp.process(result)
        assert filtered.findings == []

    def test_does_not_mutate_input(self):
        result = ReviewResult(summary="", findings=[
            make_finding(title="Bug A", file="a.py"),
            make_finding(title="Bug B", file="b.py"),
        ], warnings=["original"])
        pp = PostProcessor()
        pp.process(result)
        # Original should be unchanged
        assert result.warnings == ["original"]
