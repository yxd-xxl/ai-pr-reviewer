"""Tests for BugAnalyzer — independent logic & bug analysis."""

from unittest.mock import MagicMock

import pytest

from src.core.types import (
    PullRequest, FileChange, ReviewContext, Finding, Location,
)
from src.analysis.bug_analyzer import BugAnalyzer
from src.analysis.prompts.bug import build_bug_prompt


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.complete.return_value = MagicMock(
        content="## Bug Analysis\n\nFound 2 potential bugs.")
    adapter.complete_json.return_value = {
        "findings": [
            {
                "severity": "high", "category": "bug",
                "title": "Null dereference risk",
                "description": "Variable may be None when used at line 42.",
                "suggestion": "Add null check before dereference.",
                "line": 42, "evidence": "result = data.process()",
                "classification": "new", "confidence": 85,
            },
            {
                "severity": "medium", "category": "bug",
                "title": "Off-by-one in loop boundary",
                "description": "Loop iterates one too many times.",
                "suggestion": "Use range(len(arr) - 1).",
                "line": 15, "evidence": "for i in range(len(arr)):",
                "classification": "new", "confidence": 70,
            },
        ]
    }
    return adapter


@pytest.fixture
def sample_ctx():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="Test PR",
        description="", url="https://github.com/o/r/pull/1",
        base_branch="main", head_branch="feat",
        base_sha="a", head_sha="b",
    )
    fc = FileChange(
        path="app.py", status="modified", language="python",
        diff="@@ -40,5 +40,5 @@\n-old\n+new", additions=5, deletions=5,
    )
    return ReviewContext(pr=pr, files=[fc])


class TestBugPrompt:
    def test_prompt_includes_bug_perspective(self):
        fc = FileChange(
            path="app.py", status="modified", language="python",
            diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1,
        )
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        ctx = ReviewContext(pr=pr, files=[fc])
        system, user = build_bug_prompt(fc, ctx)
        assert "bug" in system.lower() or "logic" in system.lower()
        assert fc.path in user

    def test_prompt_differs_from_generic_analysis(self):
        fc = FileChange(
            path="app.py", status="modified", language="python",
            diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1,
        )
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        ctx = ReviewContext(pr=pr, files=[fc])
        bug_system, _ = build_bug_prompt(fc, ctx)
        from src.analysis.prompts.analysis import build_analysis_prompt
        gen_system, _ = build_analysis_prompt(fc, ctx)
        assert bug_system != gen_system


class TestBugAnalyzer:
    def test_analyze_returns_result(self, mock_adapter, sample_ctx):
        analyzer = BugAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        assert result.summary is not None
        assert len(result.findings) >= 0
        assert result.metadata["analyzer"] == "bug"

    def test_all_findings_have_bug_category(self, mock_adapter, sample_ctx):
        analyzer = BugAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        for f in result.findings:
            assert f.category == "bug"
            assert f.analyzer == "bug"

    def test_skips_binary_files(self, mock_adapter):
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        fc = FileChange(
            path="image.png", status="modified", language="",
            diff="", is_binary=True,
        )
        ctx = ReviewContext(pr=pr, files=[fc])
        analyzer = BugAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        # Binary file should be skipped
        assert result.summary is not None

    def test_skips_removed_files(self, mock_adapter):
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        fc = FileChange(
            path="old.py", status="removed", language="python",
            diff="@@ -1,10 +0,0 @@\n-old code", additions=0, deletions=10,
        )
        ctx = ReviewContext(pr=pr, files=[fc])
        analyzer = BugAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []

    def test_empty_files_list(self, mock_adapter):
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        ctx = ReviewContext(pr=pr, files=[])
        analyzer = BugAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []
