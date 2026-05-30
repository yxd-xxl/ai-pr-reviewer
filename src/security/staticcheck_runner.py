"""Staticcheck SAST runner for Go static analysis."""

import json
import subprocess
from dataclasses import dataclass


@dataclass
class StaticcheckFinding:
    issue_id: str
    severity: str       # high | medium | low (mapped from staticcheck diagnostic codes)
    file: str
    line: int
    description: str


# Maps staticcheck diagnostic code prefixes to internal severity
# SA* = static analysis (high confidence bugs)
# ST* = style/structure
# U* = unused code
_CODE_SEVERITY = {
    "SA": "high",
    "ST": "medium",
    "U": "low",
    "S": "high",   # security-related
}


def _map_severity(code: str) -> str:
    for prefix, sev in _CODE_SEVERITY.items():
        if code.startswith(prefix):
            return sev
    return "medium"


def run_staticcheck(file_paths: list[str]) -> tuple[list[StaticcheckFinding], list[str]]:
    """Run staticcheck on Go files. Returns (findings, warnings)."""
    go_files = [f for f in file_paths if f.endswith(".go")]
    if not go_files:
        return [], []

    # Exclude test files
    scan_files = [f for f in go_files
                  if "_test.go" not in f and "tests/" not in f]
    if not scan_files:
        return [], []

    try:
        result = subprocess.run(
            ["staticcheck", "-f", "json", "--"] + scan_files,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode not in (0, 1):
            return [], [f"staticcheck exit code {result.returncode}: {result.stderr[:200]}"]

        findings = _parse_output(result.stdout)
        if not findings and result.stdout.strip():
            return [], ["staticcheck output could not be parsed"]

        return findings, []
    except FileNotFoundError:
        return [], ["staticcheck is not installed — skipping SAST for Go"]
    except subprocess.TimeoutExpired:
        return [], ["staticcheck scan timed out"]


def _parse_output(output: str) -> list[StaticcheckFinding]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    findings: list[StaticcheckFinding] = []
    for entry in data:
        loc = entry.get("location", {})
        code = entry.get("code", "")
        findings.append(StaticcheckFinding(
            issue_id=code,
            severity=_map_severity(code),
            file=loc.get("file", ""),
            line=loc.get("line", 0),
            description=entry.get("message", ""),
        ))
    return findings
