"""Tests for unified SAST dispatcher."""

from unittest.mock import patch, MagicMock

from src.security.runner import run_sast, SastResult


class TestSastResult:
    def test_dataclass_fields(self):
        r = SastResult(language="python", findings=[], warnings=[])
        assert r.language == "python"
        assert r.findings == []

    def test_defaults(self):
        r = SastResult(language="python")
        assert r.findings == []
        assert r.warnings == []


class TestRunSast:
    def test_returns_empty_dict_for_empty_file_list(self):
        result = run_sast([])
        assert result == {}

    def test_dispatches_python_to_bandit(self):
        with patch("src.security.runner.run_bandit") as mock_bandit:
            mock_bandit.return_value = ([], [])
            result = run_sast(["/app/script.py"])
            assert "python" in result
            mock_bandit.assert_called()

    def test_dispatches_javascript_to_eslint(self):
        with patch("src.security.runner.run_eslint") as mock_eslint:
            mock_eslint.return_value = ([], [])
            result = run_sast(["/app/src/app.js"])
            assert "javascript" in result
            mock_eslint.assert_called()

    def test_dispatches_typescript_to_eslint(self):
        with patch("src.security.runner.run_eslint") as mock_eslint:
            mock_eslint.return_value = ([], [])
            result = run_sast(["/app/src/app.ts"])
            assert "typescript" in result
            mock_eslint.assert_called()

    def test_dispatches_go_to_staticcheck(self):
        with patch("src.security.runner.run_staticcheck") as mock_sc:
            mock_sc.return_value = ([], [])
            result = run_sast(["/app/main.go"])
            assert "go" in result
            mock_sc.assert_called()

    def test_groups_mixed_languages(self):
        with patch("src.security.runner.run_bandit") as mock_bandit, \
             patch("src.security.runner.run_eslint") as mock_eslint, \
             patch("src.security.runner.run_staticcheck") as mock_sc:
            mock_bandit.return_value = ([], [])
            mock_eslint.return_value = ([], [])
            mock_sc.return_value = ([], [])
            result = run_sast([
                "/app/script.py", "/app/app.js", "/app/main.go",
                "/app/readme.md",
            ])
            assert "python" in result
            assert "javascript" in result
            assert "go" in result
            assert "text" not in result  # unknown languages skipped

    def test_skips_languages_without_sast_tool(self):
        result = run_sast(["/app/readme.md", "/app/Dockerfile"])
        assert result == {}

    def test_captures_runner_exceptions_as_warnings(self):
        with patch("src.security.runner.run_eslint", side_effect=Exception("boom")):
            result = run_sast(["/app/app.js"])
            sast_result = result.get("javascript")
            assert sast_result is not None
            assert len(sast_result.warnings) > 0
            assert any("boom" in w or "failed" in w.lower() for w in sast_result.warnings)

    def test_runner_skips_when_files_empty_for_language(self):
        result = run_sast(["/app/script.py"])
        assert "javascript" not in result
        assert "go" not in result
