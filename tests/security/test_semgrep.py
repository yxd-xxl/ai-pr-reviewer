"""Tests for Semgrep SAST runner."""

import json
import subprocess
from unittest.mock import patch, MagicMock
from src.security.semgrep_runner import SemgrepFinding, run_semgrep


def _semgrep_output():
    return json.dumps({
        "results": [{
            "check_id": "python.lang.security.audit.eval-detected",
            "path": "/app/src/app.py",
            "start": {"line": 42, "col": 5},
            "end": {"line": 42, "col": 20},
            "extra": {
                "severity": "ERROR",
                "message": "Detected use of eval(). Use literal_eval or avoid.",
                "metadata": {"cwe": [95]},
            },
        }],
        "errors": [],
    })


class TestSemgrepFinding:
    def test_fields(self):
        f = SemgrepFinding(check_id="test.rule", severity="high", file="a.py", line=10, message="test")
        assert f.check_id == "test.rule"
        assert f.severity == "high"


class TestRunSemgrep:
    def test_returns_empty_when_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            findings, warnings = run_semgrep(["/app/app.py"])
            assert findings == []
            assert any("not installed" in w.lower() for w in warnings)

    def test_parses_json_output(self):
        output = _semgrep_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, warnings = run_semgrep(["/app/src/app.py"])
            assert len(findings) == 1
            f = findings[0]
            assert f.check_id == "python.lang.security.audit.eval-detected"
            assert f.severity == "high"
            assert f.file == "/app/src/app.py"
            assert f.line == 42
            assert f.cwe_id == "CWE-95"

    def test_maps_error_to_high(self):
        output = json.dumps({
            "results": [{"check_id": "x", "path": "a.py", "start": {"line": 1}, "end": {"line": 1},
                          "extra": {"severity": "ERROR", "message": "x"}}], "errors": []})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, _ = run_semgrep(["/app/a.py"])
            assert findings[0].severity == "high"

    def test_filters_low_severity(self):
        output = json.dumps({
            "results": [{"check_id": "x", "path": "a.py", "start": {"line": 1}, "end": {"line": 1},
                          "extra": {"severity": "INFO", "message": "x"}}], "errors": []})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, _ = run_semgrep(["/app/a.py"])
            assert len(findings) == 0

    def test_handles_invalid_json(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="not json", returncode=1)
            findings, _ = run_semgrep(["/app/a.py"])
            assert findings == []

    def test_excludes_test_files(self):
        output = _semgrep_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            run_semgrep(["/app/test_a.py", "/app/main.go"])
            args = mock_run.call_args[0][0]
            passed = [a for a in args if not a.startswith("--") and isinstance(a, str)]
            assert not any("test" in p.lower() for p in passed)
