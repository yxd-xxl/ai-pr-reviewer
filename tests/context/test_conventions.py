import pytest
from unittest.mock import patch, MagicMock
from src.context.conventions import load_conventions


class TestLoadConventions:
    def test_returns_empty_when_file_not_found(self):
        with patch("src.context.conventions._fetch_file", return_value=None):
            result = load_conventions("t", "o", "r")
            assert result == []

    def test_returns_convention_when_file_found(self):
        content = "# Project Rules\n\nUse TDD."
        with patch("src.context.conventions._fetch_file", return_value=content):
            result = load_conventions("t", "o", "r")
            assert len(result) == 1
            assert result[0].source == ".claude/CLAUDE.md"
            assert "TDD" in result[0].content

    def test_truncates_long_content(self):
        content = "x" * 3000
        with patch("src.context.conventions._fetch_file", return_value=content):
            result = load_conventions("t", "o", "r")
            assert len(result[0].content) <= 2100
            assert "truncated" in result[0].content
