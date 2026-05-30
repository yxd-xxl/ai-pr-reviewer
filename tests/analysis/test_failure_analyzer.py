"""Tests for FailureAnalyzer — exception handling, external dependency, resource lifecycle."""

from unittest.mock import MagicMock
import pytest
from src.core.types import PullRequest, FileChange, ReviewContext
from src.analysis.failure_analyzer import FailureAnalyzer
from src.analysis.prompts.failure import build_failure_prompt


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.complete.return_value = MagicMock(content="## Failure Analysis\n\nFound 2 potential failure modes.")
    adapter.complete_json.return_value = {
        "findings": [
            {"severity": "high", "category": "failure",
             "title": "Exception silently swallowed",
             "description": "Bare except at line 15 swallows all exceptions.",
             "suggestion": "Log the exception and re-raise specific types.",
             "line": 15, "evidence": "except:\n    pass",
             "classification": "new", "confidence": 55},
            {"severity": "medium", "category": "failure",
             "title": "File opened without context manager",
             "description": "File opened at line 30 without close guarantee.",
             "suggestion": "Use 'with open()' context manager.",
             "line": 30, "evidence": "f = open(path)",
             "classification": "new", "confidence": 45},
        ]
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


class TestFailurePrompt:
    def test_prompt_includes_failure_focus(self):
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[fc])
        system, user = build_failure_prompt(fc, ctx)
        assert "failure" in system.lower() or "exception" in system.lower()

    def test_prompt_differs_from_generic(self):
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[fc])
        fail_sys, _ = build_failure_prompt(fc, ctx)
        from src.analysis.prompts.analysis import build_analysis_prompt
        gen_sys, _ = build_analysis_prompt(fc, ctx)
        assert fail_sys != gen_sys


class TestFailureAnalyzer:
    def test_analyze_returns_result(self, mock_adapter, sample_ctx):
        analyzer = FailureAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        assert result.summary is not None
        assert result.metadata["analyzer"] == "failure"

    def test_all_findings_have_failure_category(self, mock_adapter, sample_ctx):
        analyzer = FailureAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        for f in result.findings:
            assert f.category == "failure"
            assert f.analyzer == "failure"

    def test_skips_binary_files(self, mock_adapter):
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        fc = FileChange(path="img.png", status="modified", language="", diff="", is_binary=True)
        ctx = ReviewContext(pr=pr, files=[fc])
        analyzer = FailureAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []

    def test_empty_files_list(self, mock_adapter):
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[])
        analyzer = FailureAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []
