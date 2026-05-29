from src.analysis.analyzer import Analyzer
from src.core.types import ReviewContext, ReviewResult, Finding


class CompositeAnalyzer(Analyzer):
    def __init__(self, analyzers: list[Analyzer]):
        self._analyzers = analyzers

    def analyze(self, context: ReviewContext) -> ReviewResult:
        all_findings: list[Finding] = []
        all_warnings: list[str] = []
        all_errors: list[str] = []
        summaries: list[str] = []
        metadata: dict = {"analyzer": "composite", "analyzers": []}

        for a in self._analyzers:
            try:
                result = a.analyze(context)
                all_findings.extend(result.findings)
                all_warnings.extend(result.warnings)
                all_errors.extend(result.errors)
                summaries.append(result.summary)
                metadata["analyzers"].append(
                    result.metadata.get("analyzer", type(a).__name__)
                )
            except Exception as e:
                name = type(a).__name__
                all_errors.append(f"{name} failed: {e}")

        return ReviewResult(
            summary="\n\n".join(summaries),
            findings=all_findings,
            metadata=metadata,
            warnings=all_warnings,
            errors=all_errors,
        )
