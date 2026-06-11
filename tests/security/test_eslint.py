"""Tests for ESLint SAST runner — JavaScript/TypeScript static analysis."""

import json
import subprocess
from unittest.mock import patch, MagicMock

from src.security.eslint_runner import ESLintFinding, run_eslint


def _eslint_output(finding: dict | None = None) -> str:
    default = {
        "ruleId": "no-eval",
        "severity": 2,
        "line": 10,
        "column": 5,
        "message": "eval can be harmful.",
        "endLine": 10,
        "endColumn": 9,
    }
    entry = finding if finding is not None else default
    return json.dumps([{
        "filePath": "/app/src/app.js",
        "messages": [entry],
        "errorCount": 1,
        "warningCount": 0,
    }])


class TestESLintFinding:
    def test_dataclass_fields(self):
        f = ESLintFinding(
            issue_id="no-eval",
            severity="high",
            file="/app/src/app.js",
            line=10,
            description="eval can be harmful.",
            rule_id="no-eval",
        )
        assert f.issue_id == "no-eval"
        assert f.severity == "high"
        assert f.line == 10


class TestRunESLint:
    def test_returns_empty_for_no_js_ts_files(self):
        findings, warnings = run_eslint(["/app/readme.md", "/app/script.py"])
        assert findings == []
        assert warnings == []

    def test_returns_empty_when_eslint_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            findings, warnings = run_eslint(["/app/src/app.js"])
            assert findings == []
            assert any("not installed" in w.lower() for w in warnings)

    def test_returns_empty_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="eslint", timeout=60)):
            findings, warnings = run_eslint(["/app/src/app.js"])
            assert findings == []
            assert any("timed out" in w.lower() for w in warnings)

    def test_parses_json_output(self):
        output = _eslint_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, warnings = run_eslint(["/app/src/app.js"])
            assert len(findings) == 1
            f = findings[0]
            assert f.issue_id == "no-eval"
            assert f.severity == "high"
            assert f.file == "/app/src/app.js"
            assert f.line == 10

    def test_filters_non_error_severity(self):
        output = _eslint_output({"ruleId": "semi", "severity": 1, "line": 3, "column": 1,
                                  "message": "Missing semicolon.", "endLine": 3, "endColumn": 2})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=0)
            findings, warnings = run_eslint(["/app/src/app.ts"])
            assert len(findings) == 0

    def test_maps_severity_error_to_high(self):
        output = _eslint_output({"ruleId": "no-unused-vars", "severity": 2, "line": 5, "column": 1,
                                  "message": "x is defined but never used.", "endLine": 5, "endColumn": 2})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, _ = run_eslint(["/app/src/app.ts"])
            assert findings[0].severity == "high"

    def test_handles_invalid_json(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="not json", returncode=1)
            findings, warnings = run_eslint(["/app/src/app.js"])
            assert findings == []
            assert any("parse" in w.lower() or "output" in w.lower() for w in warnings)

    def test_filters_only_js_ts_extensions(self):
        output = _eslint_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            run_eslint(["/app/src/app.tsx", "/app/src/util.ts", "/app/src/hello.js",
                         "/app/src/readme.md"])
            args = mock_run.call_args[0][0]
            # Only JS/TS files after '--' flag
            dash_idx = args.index("--") if "--" in args else 0
            paths = args[dash_idx + 1:]
            for path in paths:
                assert isinstance(path, str)
                assert any(path.endswith(ext) for ext in [".tsx", ".ts", ".js", ".mjs", ".jsx"])

    def test_excludes_test_files(self):
        output = _eslint_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            run_eslint(["/app/src/app.test.js", "/app/tests/helper.ts", "/app/src/main.ts"])
            args = mock_run.call_args[0][0]
            passed = [a for a in args if not a.startswith("--")]
            # test files excluded
            assert all("test" not in p.lower().split("/")[-1].replace(".test.", "") for p in passed
                       if isinstance(p, str))
