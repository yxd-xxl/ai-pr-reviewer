import pytest
from unittest.mock import MagicMock
from src.analysis.llm_analyzer import LLMAnalyzer
from src.analysis.analyzer import MockAnalyzer
from src.llm import MockLLMAdapter
from src.core.types import (
    PullRequest, ReviewContext, FileChange, DiffHunk,
)


@pytest.fixture
def ctx_with_file():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="test", description="d",
        url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
    )
    fc = FileChange(
        path="src/app.py", status="modified", language="python",
        diff="@@ -1,1 +1,1 @@\n-old\n+new", additions=1, deletions=1,
        hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1,
                        content="@@ -1,1 +1,1 @@\n-old\n+new")],
    )
    return ReviewContext(pr=pr, files=[fc])


class TestLLMAnalyzerWithMock:
    def test_integrates_with_mock_adapter(self, ctx_with_file):
        adapter = MockLLMAdapter()
        analyzer = LLMAnalyzer(adapter)
        result = analyzer.analyze(ctx_with_file)
        assert result.summary
        assert result.metadata["analyzer"] == "llm"

    def test_generates_findings_from_adapter(self, ctx_with_file):
        adapter = MockLLMAdapter()
        analyzer = LLMAnalyzer(adapter)
        result = analyzer.analyze(ctx_with_file)
        # Mock adapter returns medium severity finding
        assert len(result.findings) > 0

    def test_skips_binary_files(self):
        pr = PullRequest(
            owner="o", repo="r", number=1, title="t", description="d",
            url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
        )
        fc = FileChange(path="img.png", status="modified", language="",
                        diff="Binary files differ", is_binary=True)
        ctx = ReviewContext(pr=pr, files=[fc])
        adapter = MockLLMAdapter()
        result = LLMAnalyzer(adapter).analyze(ctx)
        assert result.findings == []
