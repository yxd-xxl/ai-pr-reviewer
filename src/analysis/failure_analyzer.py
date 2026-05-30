"""Failure mode analyzer — exception handling, external deps, resource lifecycle."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.types import ReviewContext, ReviewResult, Finding, Location
from src.analysis.analyzer import Analyzer
from src.analysis.confidence import parse_confidence
from src.analysis.prompts import build_summary_prompt
from src.analysis.prompts.failure import build_failure_prompt
from src.analysis.prompts.verify import build_verify_prompt
from src.llm import LLMAdapter


def _run_sast_unified(file_paths):
    try:
        from src.security.runner import run_sast
        return run_sast(file_paths)
    except ImportError:
        from src.security.bandit_runner import run_bandit
        f, w = run_bandit(file_paths)
        if f or w:
            return {"python": type("S", (), {"findings": f, "warnings": w, "language": "python"})()}
        return {}


class FailureAnalyzer(Analyzer):
    """Independent analyzer for failure modes and robustness issues."""

    def __init__(self, adapter: LLMAdapter, parallel: int = 4,
                 verify_all: bool = False):
        self._adapter = adapter
        self._parallel = parallel
        self._verify_all = verify_all

    def analyze(self, context: ReviewContext) -> ReviewResult:
        warnings, errors, findings = [], [], []
        sast_results = _run_sast_unified([f.path for f in context.files])
        all_sast = []
        for lang, sr in sast_results.items():
            warnings.extend(sr.warnings)
            if sr.findings:
                all_sast.extend(sr.findings)

        summary = self._summary(context, warnings, errors)

        analyzable = [fc for fc in context.files
                      if not fc.is_binary and fc.status != "removed"]
        if analyzable:
            with ThreadPoolExecutor(max_workers=min(self._parallel, len(analyzable))) as pool:
                futures = {pool.submit(self._file, fc, context, all_sast): fc
                          for fc in analyzable}
                for f in as_completed(futures):
                    try:
                        findings.extend(f.result())
                    except Exception as e:
                        errors.append(f"Failure analysis failed: {e}")

        # Verify critical/high
        verify_sevs = ("critical", "high") if not self._verify_all else ("critical", "high", "medium")
        to_verify = [f for f in findings if f.severity in verify_sevs and f.confidence >= 0.4]
        verified, rejected = [], 0
        if to_verify:
            with ThreadPoolExecutor(max_workers=min(4, len(to_verify))) as pool:
                futures = {pool.submit(self._verify, f, context): f for f in to_verify}
                for fut in as_completed(futures):
                    f = futures[fut]
                    try:
                        ok, conf, reason = fut.result()
                    except Exception:
                        verified.append(f); continue
                    if ok and conf >= 0.4:
                        f.confidence = min(f.confidence, conf); verified.append(f)
                    else:
                        warnings.append(f"Failure verify rejected: {f.title}"); rejected += 1
            if rejected:
                warnings.append(f"Failure verification filtered {rejected} finding(s)")
        for f in findings:
            if f not in to_verify:
                verified.append(f)

        return ReviewResult(summary=summary, findings=verified,
                           metadata={"analyzer": "failure", "model": "llm"},
                           warnings=warnings, errors=errors)

    def _summary(self, ctx, warnings, errors):
        try:
            s, u = build_summary_prompt(ctx)
            return self._adapter.complete(system=s, user=u).content
        except Exception as e:
            errors.append(f"Failure summary failed: {e}")
            return "## Failure Analysis\n\nFailed."

    def _file(self, fc, ctx, sast):
        s, u = build_failure_prompt(fc, ctx, sast)
        data = self._adapter.complete_json(system=s, user=u)
        return [Finding(
            severity=f.get("severity", "medium"), category="failure",
            classification=f.get("classification", "new"),
            location=Location(file=fc.path, line=f.get("line"), side="RIGHT"),
            title=f.get("title", ""), description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
            confidence=parse_confidence(f.get("confidence", 50)),
            evidence=f.get("evidence"), analyzer="failure",
        ) for f in data.get("findings", []) if parse_confidence(f.get("confidence", 50)) >= 0.35]

    def _verify(self, finding, ctx):
        for fc in ctx.files:
            if fc.path == finding.location.file:
                try:
                    s, u = build_verify_prompt(finding, fc)
                    data = self._adapter.complete_json(system=s, user=u)
                    return data.get("verified", True), parse_confidence(data.get("confidence", 75)), data.get("reason", "")
                except Exception:
                    break
        return True, finding.confidence, "verification skipped"
