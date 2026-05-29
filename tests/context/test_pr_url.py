import pytest
from src.context.pr_url import parse_pr_url, PRUrl


class TestParsePrUrl:
    def test_standard_github_pr_url(self):
        url = "https://github.com/owner/repo/pull/42"
        result = parse_pr_url(url)
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.number == 42

    def test_url_with_trailing_slash(self):
        url = "https://github.com/owner/repo/pull/42/"
        result = parse_pr_url(url)
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.number == 42

    def test_url_with_files_tab(self):
        url = "https://github.com/owner/repo/pull/42/files"
        result = parse_pr_url(url)
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.number == 42

    def test_url_with_query_params(self):
        url = "https://github.com/owner/repo/pull/42?tab=commits"
        result = parse_pr_url(url)
        assert result.number == 42

    def test_invalid_url_not_github(self):
        with pytest.raises(ValueError, match="Invalid PR/MR URL"):
            parse_pr_url("https://gitlab.com/owner/repo/pull/42")

    def test_invalid_url_no_pull(self):
        with pytest.raises(ValueError, match="Invalid PR/MR URL"):
            parse_pr_url("https://github.com/owner/repo/issues/42")

    def test_invalid_url_missing_number(self):
        with pytest.raises(ValueError, match="Invalid PR/MR URL"):
            parse_pr_url("https://github.com/owner/repo/pull/")

    def test_repo_with_dots(self):
        url = "https://github.com/owner/my.repo.app/pull/100"
        result = parse_pr_url(url)
        assert result.repo == "my.repo.app"
        assert result.number == 100
