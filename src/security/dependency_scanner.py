"""Dependency vulnerability scanner — known CVE detection for Python and JS."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DependencyVuln:
    package: str
    version: str
    cve_id: str
    severity: str       # critical | high | medium | low
    description: str
    fix_version: str = ""


def scan_python_deps(project_dir: str = ".") -> tuple[list[DependencyVuln], list[str]]:
    """Scan Python dependencies using pip-audit. Returns (vulns, warnings)."""
    req_file = Path(project_dir) / "requirements.txt"
    if not req_file.exists():
        return [], []

    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json", "-r", str(req_file)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode not in (0, 1):
            return [], [f"pip-audit exit code {result.returncode}"]

        return _parse_pip_audit(result.stdout), []
    except FileNotFoundError:
        return [], ["pip-audit is not installed — skipping Python dependency scan"]
    except subprocess.TimeoutExpired:
        return [], ["pip-audit scan timed out"]


def scan_js_deps(project_dir: str = ".") -> tuple[list[DependencyVuln], list[str]]:
    """Scan JS dependencies using npm audit. Returns (vulns, warnings)."""
    pkg_file = Path(project_dir) / "package.json"
    if not pkg_file.exists():
        return [], []

    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True, text=True, timeout=120, cwd=project_dir,
        )
        if result.returncode not in (0, 1):
            return [], [f"npm audit exit code {result.returncode}"]

        return _parse_npm_audit(result.stdout), []
    except FileNotFoundError:
        return [], ["npm is not installed — skipping JS dependency scan"]
    except subprocess.TimeoutExpired:
        return [], ["npm audit scan timed out"]


def scan_dependencies(project_dir: str = ".") -> dict[str, tuple[list, list]]:
    """Run all dependency scanners. Returns dict mapping language to (vulns, warnings)."""
    results: dict[str, tuple[list, list]] = {}
    py_vulns, py_warnings = scan_python_deps(project_dir)
    if py_vulns or py_warnings:
        results["python"] = (py_vulns, py_warnings)
    js_vulns, js_warnings = scan_js_deps(project_dir)
    if js_vulns or js_warnings:
        results["javascript"] = (js_vulns, js_warnings)
    return results


def _parse_pip_audit(output: str) -> list[DependencyVuln]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    vulns: list[DependencyVuln] = []
    for entry in data.get("dependencies", []):
        for vuln in entry.get("vulns", []):
            vulns.append(DependencyVuln(
                package=entry.get("name", ""),
                version=entry.get("version", ""),
                cve_id=vuln.get("id", ""),
                severity="high",
                description=vuln.get("description", ""),
                fix_version=", ".join(vuln.get("fix_versions", [])),
            ))
    return vulns


def _parse_npm_audit(output: str) -> list[DependencyVuln]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    vulns: list[DependencyVuln] = []
    for pkg_name, pkg_data in data.get("advisories", {}).items():
        vulns.append(DependencyVuln(
            package=pkg_name,
            version=pkg_data.get("version", ""),
            cve_id=pkg_data.get("cwe", ""),
            severity=pkg_data.get("severity", "medium"),
            description=pkg_data.get("title", ""),
            fix_version=pkg_data.get("recommendation", ""),
        ))
    return vulns
