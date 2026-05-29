import pytest
from src.delivery.markdown import render_markdown
from src.core.types import (
    PullRequest, ReviewContext, ReviewResult, Finding,
    FileChange, Location,
)


@pytest.fixture
def sample_result():
    return ReviewResult(
        summary="## Summary\n\nPR looks good overall.",
        findings=[
            Finding(
                severity="high", category="bug", location=Location(file="src/a.py", line=42),
                title="可能的空指针",
                description="变量 x 可能为 None",
                suggestion="添加 None 检查",
                confidence=0.85,
                evidence="第42行未对 x 做空值判断",
            ),
            Finding(
                severity="medium", category="style", location=Location(file="src/b.py", line=10),
                title="变量命名不规范",
                description="变量名 a 含义不明确",
                suggestion="改为有意义的名字如 user_count",
                confidence=0.7,
            ),
        ],
    )


class TestRenderMarkdown:
    def test_includes_summary(self, sample_result):
        md = render_markdown(sample_result)
        assert "Summary" in md or "summary" in md.lower()

    def test_includes_findings(self, sample_result):
        md = render_markdown(sample_result)
        assert "可能的空指针" in md
        assert "变量命名不规范" in md

    def test_includes_severity(self, sample_result):
        md = render_markdown(sample_result)
        assert "high" in md.lower()

    def test_includes_file_location(self, sample_result):
        md = render_markdown(sample_result)
        assert "src/a.py" in md or "src/a.py:42" in md

    def test_empty_findings(self):
        result = ReviewResult(summary="No issues found.", findings=[])
        md = render_markdown(result)
        assert "No issues" in md or "no issues" in md.lower()
