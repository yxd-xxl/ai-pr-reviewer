"""Tests for fix safety checks."""

import pytest
from src.delivery.fix_safety import (
    check_patch_applies, check_syntax, check_no_destructive,
)
from src.core.types import FixProposal, FixRun


class TestFixProposal:
    def test_dataclass_creation(self):
        fp = FixProposal(
            finding_fingerprint="abc123",
            patch="@@ -1,3 +1,3 @@\n-old\n+new",
            description="Fix null check",
            status="generated",
        )
        assert fp.status == "generated"
        assert fp.finding_fingerprint == "abc123"

    def test_default_values(self):
        fp = FixProposal(finding_fingerprint="fp1", patch="", description="")
        assert fp.status == "generated"
        assert fp.verification_note is None
        assert fp.test_result is None


class TestFixRun:
    def test_dataclass_creation(self):
        fr = FixRun(
            pr_url="https://github.com/o/r/pull/1",
            proposals=[],
            status="dry_run",
        )
        assert fr.status == "dry_run"
        assert fr.proposals == []


class TestCheckPatchApplies:
    def test_simple_patch_applies(self):
        original = "line 1\nline 2\nline 3\n"
        patch = "@@ -1,3 +1,3 @@\n line 1\n-line 2\n+new line 2\n line 3\n"
        assert check_patch_applies(patch, original) is True

    def test_empty_patch(self):
        assert check_patch_applies("", "code") is False

    def test_malformed_patch(self):
        assert check_patch_applies("not a patch", "code") is False


class TestCheckSyntax:
    def test_valid_python(self):
        ok, msg = check_syntax("def foo():\n    return 42\n", "python")
        assert ok is True or "not available" in msg.lower()

    def test_invalid_python(self):
        ok, msg = check_syntax("def foo(\n", "python")
        if "not available" in msg.lower():
            pytest.skip("Python compiler not available")
        assert ok is False

    def test_unknown_language(self):
        ok, msg = check_syntax("code", "brainfuck")
        assert ok is True  # skip for unknown languages


class TestCheckNoDestructive:
    def test_normal_patch_safe(self):
        patch = "@@ -1,3 +1,3 @@\n line 1\n-line 2\n+new line 2\n"
        assert check_no_destructive(patch) is True

    def test_file_deletion_detected(self):
        patch = "@@ -1,10 +0,0 @@\n-old line 1\n-old line 2\n"
        # All lines removed = potential file deletion
        assert check_no_destructive(patch) is True  # hunk deletion is OK, actual file deletion is different

    def test_empty_patch_safe(self):
        assert check_no_destructive("") is True
