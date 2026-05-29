from src.analysis.analyzer import Analyzer
from src.analysis.registry import build_analyzers, list_registered
from src.llm import LLMAdapter, MockLLMAdapter


class AnalysisMode:
    def __init__(self, categories: list[str], adapter: LLMAdapter,
                 verify_all: bool = False,
                 fix_categories: list[str] | None = None):
        self.categories = categories
        self._adapter = adapter
        self._verify_all = verify_all
        self._fix_categories = fix_categories or ["security", "bug"]

    @classmethod
    def from_categories(cls, raw: str, adapter: LLMAdapter | None = None,
                        verify_all: bool = False,
                        fix_categories: list[str] | None = None):
        if adapter is None:
            adapter = MockLLMAdapter()
        cats = [c.strip() for c in raw.split(",")]
        if "all" in cats:
            cats = ["all"]
        valid = set(list_registered().keys()) | {"all"}
        for c in cats:
            if c not in valid:
                raise ValueError(
                    f"Unknown category: '{c}'. Valid: {sorted(valid)}"
                )
        return cls(cats, adapter, verify_all=verify_all,
                   fix_categories=fix_categories)

    def build_plan(self) -> list[Analyzer]:
        return build_analyzers(self.categories, self._adapter,
                               verify_all=self._verify_all,
                               fix_categories=self._fix_categories)
