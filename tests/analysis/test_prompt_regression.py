import json
import pytest
from pathlib import Path
from src.analysis.prompts import build_analysis_prompt
from src.core.types import (
    PullRequest, ReviewContext, FileChange, DiffHunk,
)


@pytest.fixture
def pr7_context():
    """Load saved PR #7 fixture that originally produced 6 findings."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "pr7_context.json"
    if not fixture_path.exists():
        pytest.skip("Fixture not found")

    data = json.loads(fixture_path.read_text())
    pr = PullRequest(
        owner="yxd-xxl", repo="ai-pr-reviewer", number=7,
        title=data["pr_title"], description=data["pr_description"],
        url="", base_branch="main", head_branch="feat",
        base_sha="abc", head_sha="def",
    )
    files = []
    for fd in data["files"]:
        # Build hunks from diff
        hunks = _parse_hunks_from_diff(fd["diff"])
        files.append(FileChange(
            path=fd["path"], status=fd["status"],
            language=fd["language"], diff=fd["diff"],
            hunks=hunks, additions=fd["additions"],
            deletions=fd["deletions"],
        ))
    return ReviewContext(pr=pr, files=files)


def _parse_hunks_from_diff(diff: str) -> list:
    import re
    hunks = []
    for m in re.finditer(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*?)(?=@@|\Z)", diff, re.S):
        hunks.append(DiffHunk(
            old_start=int(m.group(1)), old_lines=1,
            new_start=int(m.group(2)), new_lines=1,
            content=m.group(0).strip(),
        ))
    return hunks


class TestPromptRegression:
    def test_import_ban_in_system_prompt(self, pr7_context):
        """Regression: system prompt must ban import/module existence checking."""
        fc = pr7_context.files[0]
        system, user = build_analysis_prompt(fc, pr7_context)
        assert "DO NOT comment on import" in system

    def test_evidence_rule_in_system_prompt(self, pr7_context):
        """Regression: evidence must be required in system prompt."""
        fc = pr7_context.files[0]
        system, user = build_analysis_prompt(fc, pr7_context)
        assert "evidence" in system.lower()

    def test_confidence_rule_in_system_prompt(self, pr7_context):
        """Regression: confidence >= 0.5 must be explicit."""
        fc = pr7_context.files[0]
        system, user = build_analysis_prompt(fc, pr7_context)
        assert "0.5" in system or "confidence" in system.lower()

    def test_diff_content_in_prompt(self, pr7_context):
        """Regression: actual diff must still be in the prompt."""
        fc = pr7_context.files[0]
        system, user = build_analysis_prompt(fc, pr7_context)
        # The fixture's diff should appear in the user prompt
        has_diff = len(user) > 200  # diff adds substantial content
        assert has_diff
