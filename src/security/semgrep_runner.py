"""Semgrep SAST runner — cross-language static analysis with community rules."""

import json
import subprocess
from dataclasses import dataclass


@dataclass
class SemgrepFinding:
    check_id: str
    severity: str       # high | medium | low
    file: str
    line: int
    message: str
    cwe_id: str = ""


def run_semgrep(file_paths: list[str]) -> tuple[list[SemgrepFinding], list[str]]:
    """Run Semgrep on source files. Returns (findings, warnings)."""
    if not file_paths:
        return [], []

    # Exclude test and vendor files
    scan_files = [f for f in file_paths
                  if "test" not in f.lower() and "tests/" not in f
                  and "vendor/" not in f and "node_modules/" not in f]
    if not scan_files:
        return [], []

    try:
        result = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", "--"] + scan_files,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode not in (0, 1):
            return [], [f"Semgrep exit code {result.returncode}: {result.stderr[:200]}"]

        findings = _parse_output(result.stdout)
        if not findings and result.stdout.strip():
            return [], ["Semgrep output could not be parsed"]

        # Return high + medium only (filter low)
        return [f for f in findings if f.severity in ("high", "medium")], []
    except FileNotFoundError:
        return [], ["Semgrep is not installed — skipping cross-language SAST"]
    except subprocess.TimeoutExpired:
        return [], ["Semgrep scan timed out"]


def _parse_output(output: str) -> list[SemgrepFinding]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    findings: list[SemgrepFinding] = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        severity_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
        sev = severity_map.get(extra.get("severity", "WARNING"), "low")

        cwe = ""
        metadata = extra.get("metadata", {})
        if isinstance(metadata, dict):
            cwe_list = metadata.get("cwe", [])
            if cwe_list:
                cwe = f"CWE-{cwe_list[0]}" if isinstance(cwe_list[0], (int, str)) else ""

        findings.append(SemgrepFinding(
            check_id=r.get("check_id", ""),
            severity=sev,
            file=r.get("path", ""),
            line=r.get("start", {}).get("line", 0),
            message=extra.get("message", ""),
            cwe_id=cwe,
        ))
    return findings
