"""Tests for PerformanceAnalyzer."""

from unittest.mock import MagicMock
import pytest
from src.core.types import PullRequest, FileChange, ReviewContext
from src.analysis.performance_analyzer import PerformanceAnalyzer
from src.analysis.prompts.performance import build_performance_prompt


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.complete.return_value = MagicMock(content="## Performance Analysis")
    adapter.complete_json.return_value = {
        "findings": [{
            "severity": "high", "category": "performance",
            "title": "N+1 query in loop",
            "description": "Database query inside loop causes N+1.",
            "suggestion": "Batch the query.", "line": 23,
            "evidence": "for item in items:\n    db.query(item)",
            "classification": "new", "confidence": 80,
        }]
    }
    return adapter


@pytest.fixture
def sample_ctx():
    pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                     url="https://github.com/o/r/pull/1",
                     base_branch="main", head_branch="f", base_sha="a", head_sha="b")
    fc = FileChange(path="app.py", status="modified", language="python",
                    diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
    return ReviewContext(pr=pr, files=[fc])


class TestPerfPrompt:
    def test_prompt_includes_performance_focus(self):
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[fc])
        system, user = build_performance_prompt(fc, ctx)
        assert "performance" in system.lower()

    def test_prompt_differs_from_generic(self):
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[fc])
        perf_sys, _ = build_performance_prompt(fc, ctx)
        from src.analysis.prompts.analysis import build_analysis_prompt
        gen_sys, _ = build_analysis_prompt(fc, ctx)
        assert perf_sys != gen_sys


class TestPerformanceAnalyzer:
    def test_analyze_tags_category(self, mock_adapter, sample_ctx):
        analyzer = PerformanceAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        for f in result.findings:
            assert f.category == "performance"
            assert f.analyzer == "performance"

    def test_empty_files(self, mock_adapter):
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[])
        analyzer = PerformanceAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []

    def test_metadata(self, mock_adapter, sample_ctx):
        analyzer = PerformanceAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        assert result.metadata["analyzer"] == "performance"
