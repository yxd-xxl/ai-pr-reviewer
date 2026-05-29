import pytest
from src.analysis.security_analyzer import SecurityAnalyzer
from src.analysis.prompts import build_security_prompt
from src.llm import MockLLMAdapter
from src.core.types import (
    PullRequest, ReviewContext, FileChange, DiffHunk,
)


@pytest.fixture
def ctx_with_file():
    pr = PullRequest(
        owner="o", repo="r", number=1, title="test", description="d",
        url="u", base_branch="m", head_branch="f", base_sha="a", head_sha="b",
    )
    fc = FileChange(
        path="src/app.py", status="modified", language="python",
        diff="@@ -1,1 +1,2 @@\n-x = 1\n+x = pickle.loads(data)",
        additions=1, deletions=1,
        hunks=[DiffHunk(old_start=1, old_lines=1, new_start=1, new_lines=2,
                        content="@@ -1,1 +1,2 @@\n-x = 1\n+x = pickle.loads(data)")],
    )
    return ReviewContext(pr=pr, files=[fc])


class TestSecurityAnalyzer:
    def test_analyzes_with_mock_adapter(self, ctx_with_file):
        adapter = MockLLMAdapter()
        analyzer = SecurityAnalyzer(adapter)
        result = analyzer.analyze(ctx_with_file)
        assert result.metadata["analyzer"] == "security"
        assert len(result.findings) > 0
        # Security findings should have CWE IDs from mock
        # (mock returns generic findings, security category is set by analyzer)


class TestSecurityPrompt:
    def test_includes_owasp_keywords(self, ctx_with_file):
        system, user = build_security_prompt(ctx_with_file.files[0], ctx_with_file)
        assert "injection" in (system + user).lower()
        assert "CWE" in system

    def test_requests_cwe_id(self, ctx_with_file):
        system, user = build_security_prompt(ctx_with_file.files[0], ctx_with_file)
        assert '"cwe_id"' in (system + user)
