"""ESLint SAST runner for JavaScript and TypeScript analysis."""

import json
import subprocess
from dataclasses import dataclass

from src.langs.registry import SUPPORTED_EXTENSIONS

_JS_TS_EXTENSIONS = {
    ext for lang_name, exts in [
        ("javascript", [".js", ".mjs", ".cjs", ".jsx"]),
        ("typescript", [".ts", ".tsx", ".mts", ".cts", ".d.ts"]),
    ] for ext in exts
}


@dataclass
class ESLintFinding:
    issue_id: str
    severity: str       # high | medium (mapped from ESLint error=2/warning=1)
    file: str
    line: int
    description: str
    rule_id: str = ""


def run_eslint(file_paths: list[str]) -> tuple[list[ESLintFinding], list[str]]:
    """Run ESLint on JS/TS files. Returns (findings, warnings)."""
    js_ts_files = [f for f in file_paths
                   if any(f.endswith(ext) for ext in _JS_TS_EXTENSIONS)]
    if not js_ts_files:
        return [], []

    # Exclude test files to reduce noise
    scan_files = [f for f in js_ts_files
                  if "test" not in f.lower() and "tests/" not in f
                  and ".test." not in f.lower()]
    if not scan_files:
        return [], []

    try:
        result = subprocess.run(
            ["npx", "eslint", "--format", "json", "--"] + scan_files,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode not in (0, 1):
            return [], [f"ESLint exit code {result.returncode}: {result.stderr[:200]}"]

        findings = _parse_output(result.stdout, scan_files)
        if not findings and result.stdout.strip():
            return [], ["ESLint output could not be parsed"]

        # Only return error-severity findings (severity=2),
        # matching Bandit's HIGH-only gating
        return [f for f in findings if f.severity == "high"], []
    except FileNotFoundError:
        return [], ["ESLint is not installed — skipping SAST for JS/TS"]
    except subprocess.TimeoutExpired:
        return [], ["ESLint scan timed out"]


def _parse_output(output: str, scan_files: list[str]) -> list[ESLintFinding]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    findings: list[ESLintFinding] = []
    for file_entry in data:
        file_path = file_entry.get("filePath", "")
        for msg in file_entry.get("messages", []):
            severity = "high" if msg.get("severity") == 2 else "medium"
            findings.append(ESLintFinding(
                issue_id=msg.get("ruleId", "eslint-rule"),
                severity=severity,
                file=file_path,
                line=msg.get("line", 0),
                description=msg.get("message", ""),
                rule_id=msg.get("ruleId", ""),
            ))
    return findings
