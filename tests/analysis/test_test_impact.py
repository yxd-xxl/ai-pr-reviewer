"""Tests for test impact analysis."""

from src.analysis.test_impact import (
    TestGap, analyze_test_coverage, render_test_impact_section, _guess_test_path,
)
from src.core.types import FileChange


def _file(path, status="modified"):
    return FileChange(path=path, status=status, language="python", diff="x", additions=1, deletions=0)


class TestGuessTestPath:
    def test_src_to_tests(self):
        assert _guess_test_path("src/auth.py") == "tests/test_auth.py"

    def test_already_test_prefix(self):
        # Already a test file — stays the same
        assert "tests" in _guess_test_path("tests/test_auth.py")


class TestAnalyzeTestCoverage:
    def test_missing_test_gap(self):
        fc = _file("src/auth.py")
        gaps = analyze_test_coverage([fc])
        assert len(gaps) == 1
        assert gaps[0].source_file == "src/auth.py"

    def test_test_present_no_gap(self):
        fc1 = _file("src/auth.py")
        fc2 = _file("tests/test_auth.py")
        gaps = analyze_test_coverage([fc1, fc2])
        assert len(gaps) == 0

    def test_skips_test_files(self):
        fc = _file("tests/test_auth.py")
        gaps = analyze_test_coverage([fc])
        assert len(gaps) == 0

    def test_skips_binary(self):
        fc = _file("img.png")
        fc.is_binary = True
        gaps = analyze_test_coverage([fc])
        assert len(gaps) == 0


class TestRenderSection:
    def test_no_gaps(self):
        section = render_test_impact_section([])
        assert "no corresponding" not in section.lower() or "all changed" in section.lower()

    def test_with_gaps(self):
        gap = TestGap("src/a.py", "tests/test_a.py", "Missing test")
        section = render_test_impact_section([gap])
        assert "src/a.py" in section
