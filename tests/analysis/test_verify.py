"""Tests for LLMAnalyzer._verify() independent verification."""

from unittest.mock import MagicMock

import pytest

from src.core.types import Finding, Location, FileChange, ReviewContext, PullRequest
from src.analysis.llm_analyzer import LLMAnalyzer


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.complete_json.return_value = {
        "verified": True, "confidence": 85, "reason": "Confirmed real issue."
    }
    return adapter


@pytest.fixture
def sample_ctx():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="Test", description="",
        url="https://github.com/o/r/pull/1",
        base_branch="main", head_branch="feat", base_sha="a", head_sha="b",
    )
    fc = FileChange(
        path="app.py", status="modified", language="python",
        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1,
    )
    return ReviewContext(pr=pr, files=[fc])


@pytest.fixture
def sample_finding():
    return Finding(
        severity="high", category="bug",
        location=Location(file="app.py", line=1),
        title="Test bug", description="A bug.",
        suggestion="Fix it.", confidence=0.8,
        evidence="+new", analyzer="llm",
    )


class TestVerify:
    def test_verify_accepts_finding(self, mock_adapter, sample_ctx, sample_finding):
        analyzer = LLMAnalyzer(mock_adapter)
        ok, conf, reason = analyzer._verify(sample_finding, sample_ctx)
        assert ok is True
        assert conf == 0.85
        assert isinstance(reason, str)

    def test_verify_rejects_finding(self, mock_adapter, sample_ctx, sample_finding):
        mock_adapter.complete_json.return_value = {
            "verified": False, "confidence": 25, "reason": "False positive."
        }
        analyzer = LLMAnalyzer(mock_adapter)
        ok, conf, reason = analyzer._verify(sample_finding, sample_ctx)
        assert ok is False
        assert conf == 0.25

    def test_verify_no_file_context(self, sample_finding):
        fc = FileChange(
            path="other.py", status="modified", language="python",
            diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1,
        )
        pr = PullRequest(
            owner="o", repo="r", number=1, title="T", description="",
            url="https://github.com/o/r/pull/1",
            base_branch="main", head_branch="f", base_sha="a", head_sha="b",
        )
        ctx = ReviewContext(pr=pr, files=[fc])
        adapter = MagicMock()
        analyzer = LLMAnalyzer(adapter)
        ok, conf, reason = analyzer._verify(sample_finding, ctx)
        assert ok is True  # falls back to True when no file context
        assert "no file context" in reason

    def test_verify_handles_llm_error(self, mock_adapter, sample_ctx, sample_finding):
        mock_adapter.complete_json.side_effect = Exception("LLM error")
        analyzer = LLMAnalyzer(mock_adapter)
        ok, conf, reason = analyzer._verify(sample_finding, sample_ctx)
        assert ok is True  # keeps finding on error
        assert "verification skipped" in reason
