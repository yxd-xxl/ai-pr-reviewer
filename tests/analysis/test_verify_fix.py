import pytest
from src.analysis.prompts.verify_fix import build_verify_fix_prompt
from src.core.types import Finding, Location


@pytest.fixture
def finding_with_fix():
    f = Finding(
        severity="high", category="bug",
        location=Location(file="a.py", line=42),
        title="SQL injection",
        description="User input concatenated into SQL",
        suggestion="Use parameterized query",
        confidence=0.9,
        evidence="db.execute(f'SELECT * FROM users WHERE id={user_id}')",
        fix_patch="- old\n+ new = parameterized",
    )
    return f


class TestVerifyFixPrompt:
    def test_includes_fix_patch(self, finding_with_fix):
        system, user = build_verify_fix_prompt(finding_with_fix, "db.execute()", "python")
        assert "old" in user
        assert "parameterized" in user

    def test_includes_original_code(self, finding_with_fix):
        system, user = build_verify_fix_prompt(finding_with_fix, "x = 1", "python")
        assert "x = 1" in user

    def test_requires_json_output(self, finding_with_fix):
        system, user = build_verify_fix_prompt(finding_with_fix, "code", "python")
        assert "JSON" in (system + user)

    def test_checks_safety(self, finding_with_fix):
        system, user = build_verify_fix_prompt(finding_with_fix, "code", "python")
        assert "safe" in (system + user).lower() or "side effect" in (system + user).lower()
