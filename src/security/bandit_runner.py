import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BanditFinding:
    issue_id: str
    severity: str       # HIGH | MEDIUM | LOW
    confidence: str     # HIGH | MEDIUM | LOW
    file: str
    line: int
    description: str
    more_info: str = ""


def run_bandit(file_paths: list[str]) -> tuple[list[BanditFinding], list[str]]:
    """Run Bandit SAST. Returns (findings, warnings)."""
    py_files = [f for f in file_paths if f.endswith(".py")]
    if not py_files:
        return [], []

    try:
        scan_files = [f for f in py_files if "test" not in f.lower() and "tests/" not in f]
        if not scan_files:
            return [], []

        result = subprocess.run(
            ["bandit", "-f", "json", "-q", "-ll", "--"] + scan_files,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode not in (0, 1):
            return [], [f"Bandit exit code {result.returncode}: {result.stderr[:200]}"]
        findings = _parse_output(result.stdout)
        if not findings and result.stdout.strip():
            return [], ["Bandit output could not be parsed"]
        return [f for f in findings
                if f.severity == "HIGH" and f.confidence == "HIGH"], []
    except FileNotFoundError:
        return [], ["Bandit is not installed — skipping SAST"]
    except subprocess.TimeoutExpired:
        return [], ["Bandit scan timed out"]


def _parse_output(output: str) -> list[BanditFinding]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    findings: list[BanditFinding] = []
    for r in data.get("results", []):
        findings.append(BanditFinding(
            issue_id=r.get("test_id", ""),
            severity=r.get("issue_severity", "LOW"),
            confidence=r.get("issue_confidence", "LOW"),
            file=r.get("filename", ""),
            line=r.get("line_number", 0),
            description=r.get("issue_text", ""),
            more_info=r.get("more_info", ""),
        ))
    return findings
