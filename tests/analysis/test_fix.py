import pytest
from src.analysis.prompts.fix import build_fix_prompt
from src.core.types import Finding, Location


@pytest.fixture
def sample_finding():
    return Finding(
        severity="high", category="bug",
        location=Location(file="a.py", line=42),
        title="SQL injection risk",
        description="User input directly concatenated into SQL",
        suggestion="Use parameterized query",
        confidence=0.9,
        evidence="db.execute(f'SELECT * FROM users WHERE id={user_id}')",
    )


class TestFixPrompt:
    def test_includes_finding_details(self, sample_finding):
        system, user = build_fix_prompt(sample_finding, "db.execute('SELECT')", "python")
        assert "SQL injection" in user
        assert "parameterized" in user

    def test_includes_code_snippet(self, sample_finding):
        system, user = build_fix_prompt(sample_finding, "x = 1\ny = 2", "python")
        assert "x = 1" in user

    def test_output_format_requires_json(self, sample_finding):
        system, user = build_fix_prompt(sample_finding, "code", "python")
        assert "JSON" in system + user or "json" in (system + user).lower()

    def test_empty_patch_allowed(self, sample_finding):
        system, user = build_fix_prompt(sample_finding, "code", "python")
        assert "empty" in (system + user).lower() or "no fix" in (system + user).lower()
