"""Tests for CLI commands."""

import os
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from src.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def set_token():
    old = os.getenv("GITHUB_TOKEN", "")
    os.environ["GITHUB_TOKEN"] = "test-token"
    yield
    if old:
        os.environ["GITHUB_TOKEN"] = old
    else:
        os.environ.pop("GITHUB_TOKEN", None)


class TestCLIInit:
    def test_init_creates_config(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert ".ai-pr-reviewer.yml" in result.output

    def test_init_no_overwrite(self, runner):
        with runner.isolated_filesystem():
            runner.invoke(cli, ["init"])
            result = runner.invoke(cli, ["init"])
            assert "already exists" in result.output.lower()

    def test_init_force_overwrite(self, runner):
        with runner.isolated_filesystem():
            runner.invoke(cli, ["init"])
            result = runner.invoke(cli, ["init", "--force"])
            assert result.exit_code == 0


class TestCLIInspect:
    def test_inspect_missing_token(self, runner):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_TOKEN", None)
            result = runner.invoke(cli, ["inspect", "https://github.com/o/r/pull/1"])
            assert result.exit_code == 1

    def test_inspect_invalid_url(self, runner, set_token):
        with patch("src.cli.main.GitHubClient") as mock_client:
            result = runner.invoke(cli, ["inspect", "not-a-url"])
            assert result.exit_code != 0


class TestCLIReview:
    def test_review_missing_token(self, runner):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_TOKEN", None)
            result = runner.invoke(cli, ["review", "https://github.com/o/r/pull/1"])
            assert result.exit_code == 1

    def test_review_invalid_url(self, runner, set_token):
        result = runner.invoke(cli, ["review", "not-a-url"])
        assert result.exit_code != 0


class TestCLIProfile:
    def test_profile_missing_token(self, runner):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_TOKEN", None)
            result = runner.invoke(cli, ["profile"])
            assert result.exit_code == 1

    @patch("src.cli.main.get_user_profile")
    def test_profile_shows_info(self, mock_profile, runner, set_token):
        mock_profile.return_value = {
            "login": "testuser", "name": "Test User",
            "email": "test@test.com", "public_repos": 5,
            "total_private_repos": 2,
        }
        result = runner.invoke(cli, ["profile"])
        assert result.exit_code == 0
        assert "testuser" in result.output


class TestCLIHistory:
    def test_history_empty(self, runner):
        with patch("src.cli.main.ReviewRepo") as mock_repo:
            mock_repo.return_value.get_history.return_value = []
            result = runner.invoke(cli, ["history"])
            assert "No review history" in result.output
            assert result.exit_code == 0
