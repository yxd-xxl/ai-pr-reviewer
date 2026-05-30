"""Dynamic analyzer registry — supports custom plugins."""

from src.analysis.analyzer import Analyzer
from src.analysis.llm_analyzer import LLMAnalyzer
from src.analysis.security_analyzer import SecurityAnalyzer
from src.analysis.style_analyzer import StyleAnalyzer
from src.llm import LLMAdapter

_registry: dict[str, type[Analyzer]] = {}


def register(category: str, analyzer_cls: type[Analyzer]):
    _registry[category] = analyzer_cls


def get_analyzer(category: str) -> type[Analyzer] | None:
    return _registry.get(category)


def list_registered() -> dict[str, type[Analyzer]]:
    return dict(_registry)


# Built-in defaults
register("security", SecurityAnalyzer)
register("bug", LLMAnalyzer)
register("performance", LLMAnalyzer)
register("style", StyleAnalyzer)
register("architecture", LLMAnalyzer)


def build_analyzers(categories: list[str], adapter: LLMAdapter,
                    verify_all: bool = False,
                    fix_categories: list[str] | None = None) -> list[Analyzer]:
    if "all" in categories:
        return [LLMAnalyzer(adapter, fix_categories=fix_categories or [],
                            verify_all=verify_all)]

    seen = set()
    analyzers = []
    for cat in categories:
        cls = get_analyzer(cat)
        if cls and cls not in seen:
            seen.add(cls)
            if issubclass(cls, LLMAnalyzer):
                analyzers.append(cls(adapter, fix_categories=fix_categories or [],
                                     verify_all=verify_all))
            else:
                analyzers.append(cls(adapter))
    return analyzers
