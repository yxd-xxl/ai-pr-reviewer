import pytest
from src.analysis.analyzer import MockAnalyzer
from src.core.types import PullRequest, ReviewContext, FileChange, DiffHunk


@pytest.fixture
def sample_context():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="test", description="desc",
        url="https://github.com/o/r/pull/1", base_branch="main",
        head_branch="feat", base_sha="abc", head_sha="def",
    )
    f = FileChange(path="src/a.py", status="modified", language="python",
                   diff="@@ -1,1 +1,1 @@\n-old\n+new", additions=1, deletions=1,
                   hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1,
                                   content="@@ -1,1 +1,1 @@\n-old\n+new")])
    return ReviewContext(pr=pr, files=[f])


class TestMockAnalyzer:
    def test_returns_review_result_with_findings(self, sample_context):
        analyzer = MockAnalyzer()
        result = analyzer.analyze(sample_context)
        assert result.summary
        assert len(result.findings) > 0
        for f in result.findings:
            assert f.severity in ("critical", "high", "medium", "low")
            assert f.confidence > 0

    def test_metadata_includes_mock_marker(self, sample_context):
        analyzer = MockAnalyzer()
        result = analyzer.analyze(sample_context)
        assert result.metadata["analyzer"] == "mock"

    def test_no_warnings_or_errors_by_default(self, sample_context):
        analyzer = MockAnalyzer()
        result = analyzer.analyze(sample_context)
        assert result.warnings == []
        assert result.errors == []

    def test_empty_files_produces_empty_findings(self):
        analyzer = MockAnalyzer()
        pr = PullRequest(
            owner="o", repo="r", number=1, title="t", description="d",
            url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
        )
        ctx = ReviewContext(pr=pr, files=[])
        result = analyzer.analyze(ctx)
        assert result.findings == []
