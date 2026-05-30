"""Analysis budget system — controls LLM call counts, file limits, and costs."""

from dataclasses import dataclass

from src.core.types import FileChange


@dataclass
class AnalysisBudget:
    max_files: int = 20
    max_llm_calls: int = 60
    max_tokens_estimate: int = 50000
    large_pr_threshold: int = 30

    def is_large_pr(self, file_count: int) -> bool:
        return file_count > self.large_pr_threshold


class BudgetExceeded(Exception):
    pass


class BudgetTracker:
    def __init__(self, budget: AnalysisBudget):
        self.budget = budget
        self.llm_calls_used = 0
        self.files_analyzed = 0
        self.skipped_files = 0

    def record_llm_call(self, count: int = 1):
        self.llm_calls_used += count

    def record_files_analyzed(self, count: int):
        self.files_analyzed += count

    def record_skipped(self, count: int = 1):
        self.skipped_files += count

    def is_exceeded(self) -> bool:
        return (self.llm_calls_used >= self.budget.max_llm_calls or
                self.files_analyzed >= self.budget.max_files)

    @property
    def remaining_llm_calls(self) -> int:
        return max(0, self.budget.max_llm_calls - self.llm_calls_used)

    @property
    def remaining_files(self) -> int:
        return max(0, self.budget.max_files - self.files_analyzed)


def estimate_tokens(files: list[FileChange]) -> int:
    """Rough token estimate: total diff chars / 4."""
    if not files:
        return 0
    total_chars = sum(len(fc.diff) + len(fc.full_content or "") for fc in files)
    return max(1, total_chars // 4)


# Files/directories that typically indicate higher review priority
_HIGH_RISK_PATTERNS = [
    "auth", "security", "perm", "token", "secret", "key", "crypto",
    "password", "login", "session", "csrf",
]


def rank_files_by_risk(files: list[FileChange], pr_title: str = "") -> list[FileChange]:
    """Rank files by review priority. Security/auth files first, then by change size."""
    def _score(fc: FileChange) -> int:
        score = 0
        path_lower = fc.path.lower()
        # Security/auth patterns
        for pattern in _HIGH_RISK_PATTERNS:
            if pattern in path_lower:
                score += 100
                break
        # Core source files rank higher than docs/tests
        if path_lower.startswith("src/"):
            score += 50
        elif "test" in path_lower or path_lower.endswith(".md"):
            score -= 20
        # Larger changes are riskier
        score += min(fc.additions + fc.deletions, 100)
        return score

    return sorted(files, key=_score, reverse=True)
