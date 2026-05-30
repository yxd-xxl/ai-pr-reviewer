"""Tests for architecture boundary checker."""

from src.analysis.boundary_checker import (
    BoundaryRule, BoundaryConfig, check_boundaries, DEFAULT_RULES, load_boundary_config,
)
from src.core.types import FileChange


def _file(path, content):
    return FileChange(path=path, status="modified", language="python",
                      diff=content, additions=1, deletions=0, full_content=content)


class TestBoundaryRule:
    def test_fields(self):
        r = BoundaryRule(name="test", description="desc", pattern="import os", severity="medium")
        assert r.name == "test"
        assert r.severity == "medium"


class TestDefaultRules:
    def test_has_builtin_rules(self):
        assert len(DEFAULT_RULES) >= 3


class TestCheckBoundaries:
    def test_detects_core_importing_context(self):
        fc = _file("src/core/types.py",
                    "from src.context.github_client import GitHubClient")
        findings = check_boundaries([fc])
        # Should detect: core importing from context/ violates hexagonal arch
        assert len(findings) >= 1, f"Expected boundary violations, got {len(findings)}"

    def test_detects_hardcoded_secret(self):
        fc = _file("src/app.py", "API_KEY = 'sk-abc123def456'\n")
        findings = check_boundaries([fc])
        assert any("credential" in f.title.lower() or "secret" in f.title.lower() for f in findings)

    def test_no_violation_clean_code(self):
        fc = _file("src/core/types.py", "from dataclasses import dataclass\n")
        findings = check_boundaries([fc])
        assert len(findings) == 0

    def test_skips_binary(self):
        fc = _file("img.png", "")
        fc.is_binary = True
        findings = check_boundaries([fc])
        assert len(findings) == 0

    def test_allowlist_excludes(self):
        config = BoundaryConfig(
            rules=[BoundaryRule(name="test", description="",
                   pattern=r'from\s+src\.context\.github_client\s+import', severity="high")],
            allowlist=["github_client"],
        )
        fc = _file("src/core/types.py", "from src.context.github_client import GitHubClient\n")
        findings = check_boundaries([fc], config)
        # With allowlist containing github_client, this import should be excluded
        assert len(findings) == 0


class TestLoadConfig:
    def test_defaults_when_no_file(self):
        config = load_boundary_config("/nonexistent/path.yml")
        assert len(config.rules) >= 3
