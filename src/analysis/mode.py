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
    def __init__(self, categories: list[str], adapter: LLMAdapter):
        self.categories = categories
        self._adapter = adapter

    @classmethod
    def from_categories(cls, raw: str, adapter: LLMAdapter | None = None):
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
        return cls(cats, adapter)

    def build_plan(self) -> list[Analyzer]:
        if "all" in self.categories:
            return [LLMAnalyzer(self._adapter)]

        analyzer_classes: set[type[Analyzer]] = set()
        for cat in self.categories:
            analyzer_classes.add(CATEGORY_MAP[cat])

        return [cls(self._adapter) for cls in analyzer_classes]
