"""Tests for blast radius impact analysis."""

from src.analysis.blast_radius import (
    BlastRadius, compute_blast_radius, format_blast_radius_report,
    blast_radius_risk_penalty,
)
from src.core.types import FileChange


def _file(path, content, status="modified"):
    return FileChange(path=path, status=status, language="python",
                      diff=content, additions=1, deletions=0, full_content=content)


class TestBlastRadius:
    def test_defaults(self):
        b = BlastRadius()
        assert b.risk_level == "low"
        assert b.total_affected == 0

    def test_level_computation(self):
        b = BlastRadius(affected_files=["a"] * 6)
        b._compute_level()
        assert b.risk_level == "medium"

    def test_critical_level(self):
        b = BlastRadius(affected_functions=["f"] * 30)
        b._compute_level()
        assert b.risk_level == "critical"


class TestComputeBlastRadius:
    def test_single_file_no_callers(self):
        fc = _file("src/app.py", "def foo():\n    pass\n")
        radius = compute_blast_radius([fc])
        assert radius.risk_level == "low"

    def test_multiple_files(self):
        f1 = _file("src/a.py", "def foo():\n    bar()\n")
        f2 = _file("src/b.py", "def bar():\n    pass\n")
        radius = compute_blast_radius([f1, f2])
        assert "src.a" in radius.affected_files or len(radius.affected_files) >= 1

    def test_skips_binary(self):
        fc = _file("img.png", "")
        fc.is_binary = True
        radius = compute_blast_radius([fc])
        assert radius.total_affected == 0


class TestFormatReport:
    def test_includes_risk_level(self):
        b = BlastRadius(risk_level="high", affected_functions=["a.foo", "b.bar"])
        report = format_blast_radius_report(b)
        assert "HIGH" in report
        assert "a.foo" in report


class TestRiskPenalty:
    def test_low_zero(self):
        assert blast_radius_risk_penalty(BlastRadius(risk_level="low")) == 0

    def test_critical_max(self):
        assert blast_radius_risk_penalty(BlastRadius(risk_level="critical")) == 20
