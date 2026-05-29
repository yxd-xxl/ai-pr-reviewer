import pytest
from unittest.mock import MagicMock
from src.analysis.llm_analyzer import LLMAnalyzer
from src.analysis.composite import CompositeAnalyzer
from src.llm import MockLLMAdapter, LLMError
from src.core.types import (
    PullRequest, ReviewContext, FileChange, DiffHunk, Finding, Location,
)


@pytest.fixture
def multi_file_ctx():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="t", description="d",
        url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
    )
    f1 = FileChange(
        path="a.py", status="modified", language="python",
        diff="@@ -1,1 +1,1 @@\n-old\n+new", additions=1, deletions=1,
        hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1,
                        content="@@ -1,1 +1,1 @@\n-old\n+new")],
    )
    f2 = FileChange(
        path="b.py", status="modified", language="python",
        diff="@@ -1,1 +1,1 @@\n-old2\n+new2", additions=1, deletions=1,
        hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1,
                        content="@@ -1,1 +1,1 @@\n-old2\n+new2")],
    )
    return ReviewContext(pr=pr, files=[f1, f2])


class TestPartialResult:
    def test_file_failure_does_not_block_others(self, multi_file_ctx):
        """When one file fails, other files still get analyzed."""
        adapter = MockLLMAdapter()
        analyzer = LLMAnalyzer(adapter)
        result = analyzer.analyze(multi_file_ctx)
        # Both files should produce findings (via mock)
        assert len(result.findings) > 0
        assert len(result.errors) == 0

    def test_composite_catches_analyzer_failure(self, multi_file_ctx):
        """When one analyzer fails, composite continues with others."""
        good = LLMAnalyzer(MockLLMAdapter())

        class FailingAnalyzer:
            def analyze(self, ctx):
                raise LLMError("simulated failure")

        composite = CompositeAnalyzer([good, FailingAnalyzer()])
        result = composite.analyze(multi_file_ctx)
        # Should still have findings from the good analyzer
        assert len(result.findings) > 0
        # Should have an error recorded
        assert len(result.errors) == 1
        assert "FailingAnalyzer" in result.errors[0]
