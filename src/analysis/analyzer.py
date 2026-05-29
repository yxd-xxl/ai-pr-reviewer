from abc import ABC, abstractmethod

from src.core.types import ReviewContext, ReviewResult, Finding, Location


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, context: ReviewContext) -> ReviewResult:
        ...


class MockAnalyzer(Analyzer):
    """Returns fixed review results for testing the full pipeline."""

    def analyze(self, context: ReviewContext) -> ReviewResult:
        findings: list[Finding] = []
        for f in context.files:
            if not f.hunks:
                continue
            h = f.hunks[0]
            line = h.new_start + h.new_lines // 2
            findings.append(Finding(
                severity="medium",
                category="style",
                location=Location(file=f.path, line=line, side="RIGHT"),
                title=f"Review suggestion for {f.path}",
                description=f"File `{f.path}` was {f.status} ({f.additions}+/{f.deletions}-).",
                suggestion="Consider adding tests for this change.",
                confidence=0.75,
                evidence=f"Hunk at line {h.new_start}: {h.content[:120]}...",
                analyzer="mock",
            ))

        return ReviewResult(
            summary=f"## Mock Review\n\nAnalyzed {len(context.files)} file(s) in PR "
                    f"[{context.pr.title}]({context.pr.url}).\n\n"
                    f"Generated {len(findings)} finding(s).\n\n"
                    f"> This is a mock analysis. Configure LLM_PROVIDER for real AI review.",
            findings=findings,
            metadata={"analyzer": "mock", "model": "none"},
        )
