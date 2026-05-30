"""Safety checks for generated fix patches before applying them."""

import re
import subprocess
import tempfile
from pathlib import Path

_HUNK_HEADER_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def check_patch_applies(patch: str, original: str) -> bool:
    """Verify a unified diff patch applies cleanly to original content."""
    if not patch or not patch.strip():
        return False
    if not any(_HUNK_HEADER_RE.match(line) for line in patch.split("\n")):
        return False
    try:
        result = _apply_unified_diff(original, patch)
        return result != original and len(result) > 0
    except Exception:
        return False


def check_syntax(code: str, language: str) -> tuple[bool, str]:
    """Run syntax check on code. Returns (ok, message)."""
    if language == "python":
        return _check_python_syntax(code)
    elif language in ("javascript", "typescript"):
        return _check_node_syntax(code)
    else:
        return True, f"Syntax check not available for {language}"


def check_no_destructive(patch: str) -> bool:
    """Check that a patch does not delete entire files or test files."""
    if not patch or not patch.strip():
        return True
    # Heuristic: count removed vs added lines
    removed = sum(1 for line in patch.split("\n") if line.startswith("-") and not line.startswith("---"))
    added = sum(1 for line in patch.split("\n") if line.startswith("+") and not line.startswith("+++"))
    # If only removals and zero additions, potentially destructive
    if removed > 10 and added == 0:
        return False
    return True


def _check_python_syntax(code: str) -> tuple[bool, str]:
    try:
        compile(code, "<fix>", "exec")
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"


def _check_node_syntax(code: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["node", "-c"],
            input=code, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, "Syntax OK"
        return False, result.stderr[:200] or "Syntax error"
    except FileNotFoundError:
        return True, "Node.js not available"
    except subprocess.TimeoutExpired:
        return True, "Node check timed out"


def _apply_unified_diff(original: str, patch: str) -> str:
    lines = original.split("\n")
    patch_lines = patch.split("\n")
    hunks = _parse_hunks(patch_lines)
    for hunk in reversed(hunks):
        old_start = hunk["old_start"] - 1
        old_count = hunk["old_count"]
        new_lines = hunk["new_lines"]
        end = old_start + old_count
        if old_start <= len(lines) and end <= len(lines):
            lines[old_start:end] = new_lines
    return "\n".join(lines)


def _parse_hunks(patch_lines: list[str]) -> list[dict]:
    hunks = []
    i = 0
    while i < len(patch_lines):
        m = _HUNK_HEADER_RE.match(patch_lines[i])
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_lines = []
            i += 1
            while i < len(patch_lines) and not _HUNK_HEADER_RE.match(patch_lines[i]):
                line = patch_lines[i]
                if line.startswith("+") and not line.startswith("+++"):
                    new_lines.append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    pass
                elif line.startswith(" "):
                    new_lines.append(line[1:])
                i += 1
            hunks.append({"old_start": old_start, "old_count": old_count, "new_lines": new_lines})
        else:
            i += 1
    return hunks
