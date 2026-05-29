from src.analysis.analyzer import Analyzer
from src.analysis.llm_analyzer import LLMAnalyzer
from src.analysis.security_analyzer import SecurityAnalyzer
from src.llm import LLMAdapter, MockLLMAdapter

CATEGORY_MAP: dict[str, type[Analyzer]] = {
    "security": SecurityAnalyzer,
    "bug": LLMAnalyzer,
    "performance": LLMAnalyzer,
    "style": LLMAnalyzer,
    "architecture": LLMAnalyzer,
}


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
        valid = {"all", "security", "bug", "performance", "style", "architecture"}
        for c in cats:
            if c not in valid:
                raise ValueError(
                    f"Unknown category: '{c}'. Valid: {sorted(valid)}"
                )
        return cls(cats, adapter, verify_all=verify_all,
                   fix_categories=fix_categories)

    def build_plan(self) -> list[Analyzer]:
        if "all" in self.categories:
            return [LLMAnalyzer(self._adapter,
                                fix_categories=self._fix_categories,
                                verify_all=self._verify_all)]

        analyzer_classes: set[type[Analyzer]] = set()
        for cat in self.categories:
            analyzer_classes.add(CATEGORY_MAP[cat])

        return [cls(self._adapter) for cls in analyzer_classes]
