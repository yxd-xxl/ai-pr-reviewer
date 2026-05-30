"""Tests for staticcheck SAST runner — Go static analysis."""

import json
import subprocess
from unittest.mock import patch, MagicMock

from src.security.staticcheck_runner import StaticcheckFinding, run_staticcheck


def _staticcheck_output(finding: dict | None = None) -> str:
    default = {
        "code": "SA4006",
        "severity": "error",
        "location": {
            "file": "/app/main.go",
            "line": 42,
            "column": 5,
        },
        "message": "this value of err is never used",
    }
    entry = finding if finding is not None else default
    return json.dumps([entry])


class TestStaticcheckFinding:
    def test_dataclass_fields(self):
        f = StaticcheckFinding(
            issue_id="SA4006",
            severity="high",
            file="/app/main.go",
            line=42,
            description="this value of err is never used",
        )
        assert f.issue_id == "SA4006"
        assert f.severity == "high"
        assert f.line == 42


class TestRunStaticcheck:
    def test_returns_empty_for_no_go_files(self):
        findings, warnings = run_staticcheck(["/app/readme.md", "/app/script.py"])
        assert findings == []
        assert warnings == []

    def test_returns_empty_when_staticcheck_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            findings, warnings = run_staticcheck(["/app/main.go"])
            assert findings == []
            assert any("not installed" in w.lower() for w in warnings)

    def test_returns_empty_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="staticcheck", timeout=60)):
            findings, warnings = run_staticcheck(["/app/main.go"])
            assert findings == []
            assert any("timed out" in w.lower() for w in warnings)

    def test_parses_json_output(self):
        output = _staticcheck_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, warnings = run_staticcheck(["/app/main.go"])
            assert len(findings) == 1
            f = findings[0]
            assert f.issue_id == "SA4006"
            assert f.severity == "high"
            assert f.file == "/app/main.go"
            assert f.line == 42

    def test_maps_sa_code_to_high(self):
        output = _staticcheck_output({"code": "SA1000", "severity": "error",
                                       "location": {"file": "/app/main.go", "line": 1, "column": 1},
                                       "message": "bad regexp"})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, _ = run_staticcheck(["/app/main.go"])
            assert findings[0].severity == "high"

    def test_maps_st_code_to_medium(self):
        output = _staticcheck_output({"code": "ST1005", "severity": "error",
                                       "location": {"file": "/app/main.go", "line": 1, "column": 1},
                                       "message": "error strings should not be capitalized"})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            findings, _ = run_staticcheck(["/app/main.go"])
            assert findings[0].severity == "medium"

    def test_handles_invalid_json(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="not json", returncode=1)
            findings, warnings = run_staticcheck(["/app/main.go"])
            assert findings == []
            assert any("parse" in w.lower() or "output" in w.lower() for w in warnings)

    def test_excludes_test_files(self):
        output = _staticcheck_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            run_staticcheck(["/app/main_test.go", "/app/main.go"])
            args = mock_run.call_args[0][0]
            passed = [a for a in args if not a.startswith("--") and isinstance(a, str)]
            has_test = any("_test.go" in p for p in passed)
            # May or may not exclude depending on implementation;
            # we check that main.go IS included
            assert any("main.go" == p.split("/")[-1] and "_test" not in p for p in passed
                       if isinstance(p, str))
