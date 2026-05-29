import pytest
from src.analysis.mode import AnalysisMode
from src.analysis.composite import CompositeAnalyzer
from src.analysis.analyzer import MockAnalyzer
from src.analysis.llm_analyzer import LLMAnalyzer
from src.analysis.security_analyzer import SecurityAnalyzer
from src.llm import MockLLMAdapter
from src.core.types import (
    PullRequest, ReviewContext, FileChange, DiffHunk,
)


@pytest.fixture
def sample_ctx():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="t", description="d",
        url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
    )
    fc = FileChange(
        path="a.py", status="modified", language="python",
        diff="@@ -1,1 +1,1 @@\n-old\n+new", additions=1, deletions=1,
        hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=1,
                        content="@@ -1,1 +1,1 @@\n-old\n+new")],
    )
    return ReviewContext(pr=pr, files=[fc])


class TestAnalysisMode:
    def test_default_all_includes_llm_analyzer(self):
        mode = AnalysisMode.from_categories("all")
        plan = mode.build_plan()
        assert len(plan) == 1
        assert isinstance(plan[0], LLMAnalyzer)

    def test_security_only(self):
        mode = AnalysisMode.from_categories("security")
        plan = mode.build_plan()
        assert len(plan) == 1
        assert isinstance(plan[0], SecurityAnalyzer)

    def test_multiple_categories(self):
        mode = AnalysisMode.from_categories("bug,style")
        plan = mode.build_plan()
        assert len(plan) == 1  # LLMAnalyzer covers both
        assert isinstance(plan[0], LLMAnalyzer)

    def test_security_and_bug(self):
        mode = AnalysisMode.from_categories("security,bug")
        plan = mode.build_plan()
        assert len(plan) == 2
        types = [type(a).__name__ for a in plan]
        assert "SecurityAnalyzer" in types
        assert "LLMAnalyzer" in types

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            AnalysisMode.from_categories("invalid")


class TestCompositeAnalyzer:
    def test_runs_analyzers_and_merges(self, sample_ctx):
        # Use mock adapter for both
        plan = [
            LLMAnalyzer(MockLLMAdapter()),
            SecurityAnalyzer(MockLLMAdapter()),
        ]
        composite = CompositeAnalyzer(plan)
        result = composite.analyze(sample_ctx)
        assert len(result.findings) > 0
        analyzers_used = {f.analyzer for f in result.findings}
        assert len(analyzers_used) >= 1

    def test_merges_warnings_and_errors(self, sample_ctx):
        plan = [LLMAnalyzer(MockLLMAdapter())]
        composite = CompositeAnalyzer(plan)
        result = composite.analyze(sample_ctx)
        assert isinstance(result.warnings, list)
        assert isinstance(result.errors, list)
