import pytest
from src.analysis.prompts import build_summary_prompt, build_analysis_prompt
from src.core.types import PullRequest, FileChange, ReviewContext, DiffHunk


@pytest.fixture
def sample_context():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="Add login",
        description="Implements user login with JWT",
        url="https://github.com/o/r/pull/1", base_branch="main",
        head_branch="feat", base_sha="abc", head_sha="def",
    )
    f = FileChange(
        path="src/auth.py", status="modified", language="python",
        diff="@@ -1,3 +1,10 @@\n import os\n+import jwt\n+def login():\n+    pass",
        additions=10, deletions=3,
        hunks=[DiffHunk(old_start=1, old_lines=3, new_start=1, new_lines=10,
                        content="@@ -1,3 +1,10 @@\n import os\n+import jwt\n+...")],
    )
    return ReviewContext(pr=pr, files=[f])


class TestBuildSummaryPrompt:
    def test_includes_pr_title(self, sample_context):
        system, user = build_summary_prompt(sample_context)
        assert "Add login" in user

    def test_includes_file_list(self, sample_context):
        system, user = build_summary_prompt(sample_context)
        assert "src/auth.py" in user

    def test_system_prompt_defines_role(self, sample_context):
        system, user = build_summary_prompt(sample_context)
        assert "code review" in system.lower() or "reviewer" in system.lower()


class TestBuildAnalysisPrompt:
    def test_includes_file_path(self, sample_context):
        system, user = build_analysis_prompt(sample_context.files[0], sample_context)
        assert "src/auth.py" in user

    def test_includes_diff_content(self, sample_context):
        system, user = build_analysis_prompt(sample_context.files[0], sample_context)
        assert "import jwt" in user

    def test_requests_json_output(self, sample_context):
        system, user = build_analysis_prompt(sample_context.files[0], sample_context)
        assert "JSON" in (system + user)
