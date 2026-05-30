"""Bug-focused analyzer — logic errors, state issues, failure modes."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.types import ReviewContext, ReviewResult, Finding, Location
from src.analysis.analyzer import Analyzer
from src.analysis.confidence import parse_confidence
from src.analysis.prompts import build_summary_prompt
from src.analysis.prompts.bug import build_bug_prompt
from src.analysis.prompts.verify import build_verify_prompt
from src.llm import LLMAdapter


def _run_sast_unified(file_paths: list[str]) -> dict:
    """Run SAST with unified interface. Falls back to bandit if dispatcher unavailable."""
    try:
        from src.security.runner import run_sast
        return run_sast(file_paths)
    except ImportError:
        from src.security.bandit_runner import run_bandit
        findings, warnings = run_bandit(file_paths)
        return {"python": type("SastResult", (), {
            "findings": findings, "warnings": warnings, "language": "python",
        })()} if findings or warnings else {}


class BugAnalyzer(Analyzer):
    """Independent analyzer for logic bugs, state issues, and failure modes."""

    def __init__(self, adapter: LLMAdapter, parallel: int = 4,
                 verify_all: bool = False):
        self._adapter = adapter
        self._parallel = parallel
        self._verify_all = verify_all

    def analyze(self, context: ReviewContext) -> ReviewResult:
        warnings: list[str] = []
        errors: list[str] = []
        findings: list[Finding] = []

        # SAST pre-filter
        file_paths = [f.path for f in context.files]
        sast_results = _run_sast_unified(file_paths)
        all_sast_findings: list = []
        for lang, sr in sast_results.items():
            warnings.extend(sr.warnings)
            if sr.findings:
                all_sast_findings.extend(sr.findings)
                warnings.append(
                    f"{lang.title()} SAST: {len(sr.findings)} finding(s)"
                )

        # Summary
        summary = self._generate_summary(context, warnings, errors)

        # Per-file bug analysis (parallel)
        analyzable = [fc for fc in context.files
                      if not fc.is_binary and fc.status != "removed"]

        if analyzable:
            with ThreadPoolExecutor(max_workers=min(self._parallel, len(analyzable))) as pool:
                futures = {
                    pool.submit(self._analyze_file, fc, context, all_sast_findings): fc
                    for fc in analyzable
                }
                for f in as_completed(futures):
                    fc = futures[f]
                    try:
                        file_findings = f.result()
                        findings.extend(file_findings)
                    except Exception as e:
                        errors.append(f"Bug analysis failed for {fc.path}: {e}")

        # Independent verification
        verify_sevs = ("critical", "high") if not self._verify_all else ("critical", "high", "medium")
        to_verify = [f for f in findings
                     if f.severity in verify_sevs and f.confidence >= 0.5]
        verified: list[Finding] = []
        rejected_count = 0

        if to_verify:
            with ThreadPoolExecutor(max_workers=min(4, len(to_verify))) as pool:
                futures = {pool.submit(self._verify, f, context): f for f in to_verify}
                for fut in as_completed(futures):
                    f = futures[fut]
                    try:
                        v_ok, v_conf, v_reason = fut.result()
                    except Exception as e:
                        warnings.append(f"Verification failed for '{f.title}': {e}")
                        verified.append(f)
                        continue
                    if v_ok and v_conf >= 0.5:
                        f.confidence = min(f.confidence, v_conf)
                        verified.append(f)
                    else:
                        warnings.append(f"Verification rejected: {f.title} ({v_reason})")
                        rejected_count += 1
            if rejected_count:
                warnings.append(f"Bug verification filtered {rejected_count} finding(s)")

        for f in findings:
            if f not in to_verify:
                verified.append(f)

        return ReviewResult(
            summary=summary,
            findings=verified,
            metadata={"analyzer": "bug", "model": "llm"},
            warnings=warnings,
            errors=errors,
        )

    def _generate_summary(self, ctx: ReviewContext, warnings: list, errors: list) -> str:
        try:
            system, user = build_summary_prompt(ctx)
            resp = self._adapter.complete(system=system, user=user)
            return resp.content
        except Exception as e:
            errors.append(f"Bug summary generation failed: {e}")
            return f"## Bug Analysis\n\nFailed to generate: {e}"

    def _analyze_file(self, fc, ctx: ReviewContext,
                      sast_findings: list | None = None) -> list[Finding]:
        system, user = build_bug_prompt(fc, ctx, sast_findings)
        data = self._adapter.complete_json(system=system, user=user)
        return [Finding(
            severity=f.get("severity", "medium"),
            classification=f.get("classification", "new"),
            category="bug",
            location=Location(file=fc.path, line=f.get("line"), side="RIGHT"),
            title=f.get("title", "Untitled bug"),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
            confidence=parse_confidence(f.get("confidence", 50)),
            evidence=f.get("evidence"),
            analyzer="bug",
        ) for f in data.get("findings", []) if parse_confidence(f.get("confidence", 50)) >= 0.5]

    def _verify(self, finding: Finding, ctx: ReviewContext) -> tuple[bool, float, str]:
        fc_match = None
        for fc in ctx.files:
            if fc.path == finding.location.file:
                fc_match = fc
                break
        if fc_match is None:
            return True, finding.confidence, "no file context"

        try:
            system, user = build_verify_prompt(finding, fc_match)
            data = self._adapter.complete_json(system=system, user=user)
            verified = data.get("verified", True)
            conf = parse_confidence(data.get("confidence", 75))
            reason = data.get("reason", "")
            return verified, conf, reason
        except Exception:
            return True, finding.confidence, "verification skipped"
