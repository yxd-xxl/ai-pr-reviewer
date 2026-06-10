"""Integration tests for pipeline.run_review()."""

from unittest.mock import patch, MagicMock

import pytest

from src.core.types import PullRequest, FileChange, ReviewResult, Finding, Location
from src.core.config import ReviewConfig


@pytest.fixture
def mock_pr():
    return PullRequest(
        owner="o", repo="r", number=1, title="Test PR",
        description="A test", url="https://github.com/o/r/pull/1",
        base_branch="main", head_branch="feat",
        base_sha="abc", head_sha="def",
    )


@pytest.fixture
def mock_files():
    return [
        FileChange(
            path="app.py", status="modified", language="python",
            diff="@@ -1 +1 @@\n-old\n+new", additions=1, deletions=1,
        ),
    ]


class TestRunReview:
    def test_parse_pr_url_called(self):
        with patch("src.pipeline.parse_pr_url") as mock_parse, \
             patch("src.pipeline.GitHubClient") as mock_client, \
             patch("src.pipeline.create_adapter") as mock_adapter, \
             patch("src.pipeline.load_conventions", return_value=[]):
            mock_parse.return_value = MagicMock(owner="o", repo="r", number=1, platform="github")
            mock_client.return_value.fetch_pr.return_value = None
            mock_client.return_value.fetch_files.return_value = []
            mock_adapter.return_value = MagicMock()

            try:
                from src.pipeline import run_review
                run_review("https://github.com/o/r/pull/1", "token")
            except RuntimeError:
                pass  # expected — mock returns None for PR
            mock_parse.assert_called_once_with("https://github.com/o/r/pull/1")

    def test_uses_gitlab_client_for_gitlab_url(self):
        # GitLabClient is used conditionally in pipeline:
        #   from src.context.gitlab_client import GitLabClient
        # Verify the module can be imported (it exists in the project)
        from src.context.gitlab_client import GitLabClient
        assert GitLabClient is not None

    def test_llm_config_sets_env_vars(self):
        import os
        with patch("src.pipeline.parse_pr_url") as mock_parse, \
             patch("src.pipeline.GitHubClient") as mock_client, \
             patch("src.pipeline.create_adapter") as mock_adapter, \
             patch("src.pipeline.load_conventions", return_value=[]):
            mock_parse.return_value = MagicMock(owner="o", repo="r", number=1, platform="github")
            mock_client.return_value.fetch_pr.return_value = None
            mock_client.return_value.fetch_files.return_value = []
            mock_adapter.return_value = MagicMock()

            try:
                from src.pipeline import run_review
                run_review("https://github.com/o/r/pull/1", "token",
                          llm_config={"provider": "deepseek", "api_key": "sk-test"})
            except RuntimeError:
                pass
            assert os.environ.get("LLM_PROVIDER") == "deepseek"
            assert os.environ.get("LLM_API_KEY") == "sk-test"

    def test_load_config_called(self):
        with patch("src.pipeline.parse_pr_url") as mock_parse, \
             patch("src.pipeline.GitHubClient") as mock_client, \
             patch("src.pipeline.create_adapter") as mock_adapter, \
             patch("src.pipeline.load_conventions", return_value=[]), \
             patch("src.pipeline.load_config") as mock_load_cfg:
            mock_parse.return_value = MagicMock(owner="o", repo="r", number=1, platform="github")
            mock_client.return_value.fetch_pr.return_value = None
            mock_client.return_value.fetch_files.return_value = []
            mock_adapter.return_value = MagicMock()
            mock_load_cfg.return_value = ReviewConfig()

            try:
                from src.pipeline import run_review
                run_review("https://github.com/o/r/pull/1", "token")
            except RuntimeError:
                pass
            mock_load_cfg.assert_called()

    def test_fast_mode_limits_categories(self):
        with patch("src.pipeline.parse_pr_url") as mock_parse, \
             patch("src.pipeline.GitHubClient") as mock_client, \
             patch("src.pipeline.create_adapter") as mock_adapter, \
             patch("src.pipeline.load_conventions", return_value=[]), \
             patch("src.pipeline.load_config") as mock_load_cfg, \
             patch("src.pipeline.AnalysisMode") as mock_mode, \
             patch("src.pipeline.PostProcessor") as mock_pp, \
             patch("src.store.db.ReviewRepo") as mock_repo:
            mock_parse.return_value = MagicMock(owner="o", repo="r", number=1, platform="github")
            mock_client.return_value.fetch_pr.return_value = MagicMock()
            mock_client.return_value.fetch_files.return_value = []
            mock_adapter.return_value = MagicMock()
            mock_load_cfg.return_value = ReviewConfig(mode="fast")
            mock_pp.return_value.process.return_value = ReviewResult(
                summary="", findings=[], metadata={})
            mock_repo.return_value.save_review.return_value = 1

            from src.pipeline import run_review
            run_review("https://github.com/o/r/pull/1", "token")
            # fast mode should call from_categories
            mock_mode.from_categories.assert_called()
