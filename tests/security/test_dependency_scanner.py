"""Tests for dependency vulnerability scanner."""

import json
import subprocess
from unittest.mock import patch, MagicMock
from src.security.dependency_scanner import (
    DependencyVuln, scan_python_deps, scan_js_deps, scan_dependencies,
)


def _pip_audit_output():
    return json.dumps({"dependencies": [{
        "name": "requests", "version": "2.25.0",
        "vulns": [{"id": "CVE-2023-32681", "description": "Proxy leak", "fix_versions": ["2.31.0"]}],
    }]})


def _npm_audit_output():
    return json.dumps({"advisories": {
        "lodash": {"version": "4.17.20", "severity": "high", "title": "Prototype pollution",
                   "cwe": "CWE-1321", "recommendation": "Upgrade to 4.17.21"},
    }})


class TestDependencyVuln:
    def test_fields(self):
        v = DependencyVuln(package="pkg", version="1.0", cve_id="CVE-123", severity="high", description="test")
        assert v.package == "pkg"
        assert v.severity == "high"


class TestScanPythonDeps:
    def test_returns_empty_when_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("pathlib.Path.exists", return_value=True):
                vulns, warnings = scan_python_deps("/fake")
                assert vulns == []
                assert any("not installed" in w.lower() for w in warnings)

    def test_parses_output(self):
        output = _pip_audit_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            with patch("pathlib.Path.exists", return_value=True):
                vulns, _ = scan_python_deps("/fake")
                assert len(vulns) == 1
                assert vulns[0].package == "requests"
                assert vulns[0].cve_id == "CVE-2023-32681"


class TestScanJSDeps:
    def test_returns_empty_when_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("pathlib.Path.exists", return_value=True):
                vulns, warnings = scan_js_deps("/fake")
                assert vulns == []
                assert any("not installed" in w.lower() for w in warnings)

    def test_parses_output(self):
        output = _npm_audit_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, returncode=1)
            with patch("pathlib.Path.exists", return_value=True):
                vulns, _ = scan_js_deps("/fake")
                assert len(vulns) == 1
                assert vulns[0].package == "lodash"


class TestScanDependencies:
    def test_combines_results(self):
        py_out = _pip_audit_output()
        js_out = _npm_audit_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=py_out, returncode=1)
            with patch("pathlib.Path.exists", return_value=True):
                results = scan_dependencies("/fake")
                assert "python" in results
