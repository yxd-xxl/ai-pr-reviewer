import pytest
from unittest.mock import MagicMock
from src.context.github_client import GitHubClient
from src.core.types import PullRequest


class TestGitHubClient:
    def test_fetch_pr_returns_pull_request(self, mocker):
        mock_github = mocker.patch("src.context.github_client.Github")
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.title = "Add login feature"
        mock_pr.body = "Implements user login"
        mock_pr.html_url = "https://github.com/owner/repo/pull/42"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feat-login"
        mock_pr.base.sha = "abc123"
        mock_pr.head.sha = "def456"
        mock_pr.user.login = "dev"
        mock_repo.get_pull.return_value = mock_pr
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token="fake-token")
        pr = client.fetch_pr("owner", "repo", 42)

        assert pr.owner == "owner"
        assert pr.repo == "repo"
        assert pr.number == 42
        assert pr.title == "Add login feature"
        assert pr.description == "Implements user login"
        assert pr.url == "https://github.com/owner/repo/pull/42"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feat-login"
        assert pr.base_sha == "abc123"
        assert pr.head_sha == "def456"
        assert pr.author == "dev"

    def test_fetch_pr_empty_description(self, mocker):
        mock_github = mocker.patch("src.context.github_client.Github")
        mock_pr = MagicMock()
        mock_pr.body = None
        mock_pr.html_url = "https://github.com/o/r/pull/1"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feat"
        mock_pr.base.sha = "abc"
        mock_pr.head.sha = "def"
        mock_pr.user.login = "dev"
        mock_github.return_value.get_repo.return_value.get_pull.return_value = mock_pr

        client = GitHubClient(token="fake-token")
        pr = client.fetch_pr("o", "r", 1)

        assert pr.description == ""
