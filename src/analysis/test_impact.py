"""Test impact analysis — detect missing test coverage for changes."""

from dataclasses import dataclass

from src.core.types import FileChange


@dataclass
class TestGap:
    source_file: str
    expected_test_file: str
    reason: str


def analyze_test_coverage(files: list[FileChange]) -> list[TestGap]:
    """Check if changed source files have corresponding test changes."""
    gaps: list[TestGap] = []
    changed_paths = {fc.path for fc in files}

    for fc in files:
        if fc.is_binary or fc.status == "removed":
            continue

        path = fc.path
        # Skip test files themselves
        if "test" in path.lower():
            continue

        # Heuristic: src/features/auth.py -> tests/features/test_auth.py
        test_path = _guess_test_path(path)

        if test_path not in changed_paths:
            gaps.append(TestGap(
                source_file=path,
                expected_test_file=test_path,
                reason=f"Source file changed but no corresponding test modification found. "
                       f"Expected test file: {test_path}",
            ))

    return gaps


def render_test_impact_section(gaps: list[TestGap]) -> str:
    """Render test impact analysis as Markdown report section."""
    if not gaps:
        return "## Test Impact\n\nAll changed source files have corresponding test changes."

    lines = [
        "## Test Impact",
        "",
        f"**Test Gaps Detected:** {len(gaps)}",
        "",
        "The following source files were changed without corresponding test changes:",
        "",
    ]
    for g in gaps:
        lines.append(f"- **{g.source_file}** → expected: `{g.expected_test_file}`")
        lines.append(f"  - {g.reason}")
    lines.append("")
    lines.append("Consider adding or updating tests for the above files.")
    return "\n".join(lines)


def _guess_test_path(source_path: str) -> str:
    """Guess the test file path for a source file."""
    parts = source_path.split("/")
    if parts[0] == "src":
        parts[0] = "tests"
    elif not parts[0].startswith("test"):
        parts.insert(0, "tests")

    filename = parts[-1]
    name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
    if not name.startswith("test_"):
        parts[-1] = f"test_{name}.{ext}"
    return "/".join(parts)
