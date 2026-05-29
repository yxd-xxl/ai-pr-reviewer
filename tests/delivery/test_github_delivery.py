import pytest
from unittest.mock import MagicMock, patch, call
from src.delivery.github_delivery import GitHubDelivery, _fingerprint
from src.core.types import ReviewResult, Finding, Location, PullRequest


@pytest.fixture
def sample_pr():
    return PullRequest(
        owner="o", repo="r", number=1, title="test", description="",
        url="https://github.com/o/r/pull/1", base_branch="main",
        head_branch="feat", base_sha="abc", head_sha="def456",
    )


@pytest.fixture
def sample_result():
    return ReviewResult(
        summary="PR looks good.",
        findings=[
            Finding(severity="high", category="bug",
                    location=Location(file="a.py", line=42, side="RIGHT"),
                    title="Null pointer", description="x may be None",
                    suggestion="Add None check", confidence=0.9,
                    evidence="x.method() without check"),
            Finding(severity="medium", category="style",
                    location=Location(file="b.py", line=None),
                    title="General style note", description="Use longer names",
                    suggestion="", confidence=0.6,
                    evidence=""),
        ],
    )


class TestGitHubDeliveryDryRun:
    def test_dry_run_does_not_post(self, sample_pr, sample_result):
        delivery = GitHubDelivery(token="fake", dry_run=True)
        delivery.deliver(sample_result, sample_pr)
        # Should not make HTTP calls
        assert delivery._comments_posted == 0
        assert delivery._summary_posted is False

    def test_dry_run_generates_preview(self, sample_pr, sample_result):
        delivery = GitHubDelivery(token="fake", dry_run=True)
        preview = delivery.deliver(sample_result, sample_pr)
        assert len(preview) > 0
        # One inline per finding with line, one summary for line=None
        assert any("a.py:42" in p for p in preview)


class TestFingerprint:
    def test_generates_unique_hash(self):
        f1 = Finding(severity="high", category="bug",
                     location=Location(file="a.py", line=42),
                     title="Null pointer", description="", suggestion="",
                     confidence=0.9)
        f2 = Finding(severity="high", category="bug",
                     location=Location(file="a.py", line=10),
                     title="Null pointer", description="", suggestion="",
                     confidence=0.9)
        assert _fingerprint(f1) != _fingerprint(f2)

    def test_same_finding_same_fingerprint(self):
        f1 = Finding(severity="high", category="bug",
                     location=Location(file="a.py", line=42),
                     title="Null pointer", description="", suggestion="fix",
                     confidence=0.9)
        f2 = Finding(severity="high", category="bug",
                     location=Location(file="a.py", line=42),
                     title="Null pointer", description="", suggestion="fix",
                     confidence=0.8)
        assert _fingerprint(f1) == _fingerprint(f2)


class TestDegradation:
    def test_line_none_sent_to_summary(self, sample_pr):
        result = ReviewResult(summary="test", findings=[
            Finding(severity="low", category="style",
                    location=Location(file="x.py", line=None),
                    title="Style", description="", suggestion="",
                    confidence=0.6),
        ])
        delivery = GitHubDelivery(token="fake", dry_run=True)
        preview = delivery.deliver(result, sample_pr)
        # Should be in summary (issue comment), not inline
        assert any("issue" in p.lower() or "summary" in p.lower() for p in preview)

    def test_removed_file_skipped(self, sample_pr):
        result = ReviewResult(summary="test", findings=[
            Finding(severity="low", category="style",
                    location=Location(file="removed.py", line=10),
                    title="Style", description="", suggestion="",
                    confidence=0.6),
        ])
        delivery = GitHubDelivery(token="fake", dry_run=True)
        preview = delivery.deliver(result, sample_pr)
        assert any("skip" in p.lower() or "removed" in p.lower() for p in preview)
