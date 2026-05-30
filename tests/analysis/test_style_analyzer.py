"""Tests for StyleAnalyzer."""

from unittest.mock import MagicMock
import pytest
from src.core.types import PullRequest, FileChange, ReviewContext
from src.analysis.style_analyzer import StyleAnalyzer
from src.analysis.prompts.style import build_style_prompt


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.complete.return_value = MagicMock(content="## Style Review")
    adapter.complete_json.return_value = {
        "findings": [{
            "severity": "low", "category": "style",
            "title": "Function too complex",
            "description": "Function has 45 lines, consider splitting.",
            "suggestion": "Extract helper functions.", "line": 10,
            "evidence": "def long_function():",
            "classification": "nit", "confidence": 60,
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


class TestStylePrompt:
    def test_prompt_includes_style_focus(self):
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[fc])
        system, user = build_style_prompt(fc, ctx)
        assert "style" in system.lower() or "quality" in system.lower()

    def test_prompt_injects_conventions(self):
        from src.core.types import ProjectConvention
        fc = FileChange(path="app.py", status="modified", language="python",
                        diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1)
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        conv = ProjectConvention(source=".claude/CLAUDE.md", type="coding_style",
                                  content="Use snake_case for functions.")
        ctx = ReviewContext(pr=pr, files=[fc], conventions=[conv])
        _, user = build_style_prompt(fc, ctx)
        assert "snake_case" in user


class TestStyleAnalyzer:
    def test_analyze_tags_category(self, mock_adapter, sample_ctx):
        analyzer = StyleAnalyzer(mock_adapter)
        result = analyzer.analyze(sample_ctx)
        for f in result.findings:
            assert f.category == "style"
            assert f.analyzer == "style"

    def test_empty_files(self, mock_adapter):
        pr = PullRequest(owner="o", repo="r", number=1, title="T", description="",
                         url="https://github.com/o/r/pull/1",
                         base_branch="main", head_branch="f", base_sha="a", head_sha="b")
        ctx = ReviewContext(pr=pr, files=[])
        analyzer = StyleAnalyzer(mock_adapter)
        result = analyzer.analyze(ctx)
        assert result.findings == []
