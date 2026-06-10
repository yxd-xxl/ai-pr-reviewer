"""Extended tests for conventions.py — fetch_file_content and edge cases."""

from unittest.mock import patch, MagicMock

import pytest

from src.context.conventions import load_conventions, fetch_file_content


class TestFetchFileContent:
    def test_returns_content_on_success(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"# Project rules\n\n- Rule 1"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            content = fetch_file_content("token", "o", "r", ".claude/CLAUDE.md")
            assert content is not None
            assert "Project rules" in content

    def test_returns_none_on_http_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("404")):
            content = fetch_file_content("token", "o", "r", "missing.md")
            assert content is None

    def test_returns_none_on_timeout(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            content = fetch_file_content("token", "o", "r", "file.md")
            assert content is None


class TestLoadConventions:
    def test_returns_empty_list_when_no_files_found(self):
        with patch("urllib.request.urlopen", side_effect=Exception("404")):
            conventions = load_conventions("token", "o", "r")
            assert conventions == []

    def test_truncates_long_content(self):
        long_content = "x" * 3000
        with patch("src.context.conventions._fetch_file", return_value=long_content):
            conventions = load_conventions("token", "o", "r")
            assert len(conventions) > 0
            # should be truncated at _MAX_LENGTH
            assert len(conventions[0].content) <= 2100  # 2000 + "... (truncated)"

    def test_includes_source_type(self):
        with patch("src.context.conventions._fetch_file", return_value="Some rules"):
            conventions = load_conventions("token", "o", "r")
            if conventions:
                assert conventions[0].source == ".claude/CLAUDE.md"
                assert conventions[0].type in ("coding_style", "project_doc")
