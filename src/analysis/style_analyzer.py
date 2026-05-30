"""Style & quality analyzer — naming, structure, conventions."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.types import ReviewContext, ReviewResult, Finding, Location
from src.analysis.analyzer import Analyzer
from src.analysis.confidence import parse_confidence
from src.analysis.prompts import build_summary_prompt
from src.analysis.prompts.style import build_style_prompt
from src.llm import LLMAdapter


class StyleAnalyzer(Analyzer):
    """Independent analyzer for code style and quality issues."""

    def __init__(self, adapter: LLMAdapter, parallel: int = 4):
        self._adapter = adapter
        self._parallel = parallel

    def analyze(self, context: ReviewContext) -> ReviewResult:
        warnings, errors, findings = [], [], []

        summary = self._summary(context, warnings, errors)

        analyzable = [fc for fc in context.files
                      if not fc.is_binary and fc.status != "removed"]
        if analyzable:
            with ThreadPoolExecutor(max_workers=min(self._parallel, len(analyzable))) as pool:
                futures = {pool.submit(self._file, fc, context): fc for fc in analyzable}
                for f in as_completed(futures):
                    try:
                        findings.extend(f.result())
                    except Exception as e:
                        errors.append(f"Style analysis failed: {e}")

        return ReviewResult(summary=summary, findings=findings,
                           metadata={"analyzer": "style", "model": "llm"},
                           warnings=warnings, errors=errors)

    def _summary(self, ctx, warnings, errors):
        try:
            s, u = build_summary_prompt(ctx)
            return self._adapter.complete(system=s, user=u).content
        except Exception as e:
            errors.append(f"Style summary failed: {e}")
            return "## Style Review\n\nFailed."

    def _file(self, fc, ctx):
        s, u = build_style_prompt(fc, ctx)
        data = self._adapter.complete_json(system=s, user=u)
        return [Finding(
            severity=f.get("severity", "low"), category="style",
            classification=f.get("classification", "nit"),
            location=Location(file=fc.path, line=f.get("line"), side="RIGHT"),
            title=f.get("title", ""), description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
            confidence=parse_confidence(f.get("confidence", 50)),
            evidence=f.get("evidence"), analyzer="style",
        ) for f in data.get("findings", []) if parse_confidence(f.get("confidence", 50)) >= 0.5]
