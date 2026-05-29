from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.types import ReviewContext, ReviewResult, Finding, Location
from src.analysis.analyzer import Analyzer
from src.analysis.confidence import parse_confidence
from src.analysis.prompts import build_summary_prompt, build_analysis_prompt
from src.analysis.prompts.verify import build_verify_prompt
from src.llm import LLMAdapter
from src.security.bandit_runner import run_bandit


class LLMAnalyzer(Analyzer):
    def __init__(self, adapter: LLMAdapter, parallel: int = 4):
        self._adapter = adapter
        self._parallel = parallel

    def analyze(self, context: ReviewContext) -> ReviewResult:
        warnings: list[str] = []
        errors: list[str] = []
        findings: list[Finding] = []

        file_paths = [f.path for f in context.files]
        bandit_findings, bandit_warnings = run_bandit(file_paths)
        warnings.extend(bandit_warnings)
        if bandit_findings:
            warnings.append(
                f"Bandit SAST: {len(bandit_findings)} finding(s) "
                f"across {len(set(b.file for b in bandit_findings))} file(s)"
            )

        summary = self._generate_summary(context, warnings, errors)

        analyzable = [fc for fc in context.files
                      if not fc.is_binary and fc.status != "removed"]

        if analyzable:
            with ThreadPoolExecutor(max_workers=min(self._parallel, len(analyzable))) as pool:
                futures = {
                    pool.submit(self._analyze_file, fc, context, bandit_findings): fc
                    for fc in analyzable
                }
                for f in as_completed(futures):
                    fc = futures[f]
                    try:
                        file_findings = f.result()
                        findings.extend(file_findings)
                    except Exception as e:
                        errors.append(f"Failed to analyze {fc.path}: {e}")

        # Stage 3: Independent verification for HIGH/CRITICAL (parallel)
        to_verify = [f for f in findings
                     if f.severity in ("critical", "high") and f.confidence >= 0.5]
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
                        verified.append(f)  # keep the finding on verification error
                        continue
                    if v_ok and v_conf >= 0.5:
                        f.confidence = min(f.confidence, v_conf)
                        verified.append(f)
                    else:
                        warnings.append(f"Verification rejected: {f.title} ({v_reason})")
                        rejected_count += 1
            if rejected_count:
                warnings.append(f"Independent verification filtered {rejected_count} finding(s)")

        for f in findings:
            if f not in to_verify:
                verified.append(f)

        return ReviewResult(
            summary=summary,
            findings=verified,
            metadata={"analyzer": "llm",
                      "model": self._adapter._model if hasattr(self._adapter, '_model') else "unknown"},
            warnings=warnings,
            errors=errors,
        )

    def _generate_summary(self, ctx: ReviewContext, warnings: list, errors: list) -> str:
        try:
            system, user = build_summary_prompt(ctx)
            resp = self._adapter.complete(system=system, user=user)
            return resp.content
        except Exception as e:
            errors.append(f"Summary generation failed: {e}")
            return f"## PR Summary\n\nFailed to generate: {e}"

    def _analyze_file(self, fc, ctx: ReviewContext,
                      bandit: list | None = None) -> list[Finding]:
        system, user = build_analysis_prompt(fc, ctx, bandit)
        data = self._adapter.complete_json(system=system, user=user)
        return [Finding(
            severity=f.get("severity", "medium"),
            classification=f.get("classification", "new"),
            category=f.get("category", "style"),
            location=Location(file=fc.path, line=f.get("line"), side="RIGHT"),
            title=f.get("title", "Untitled finding"),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
            confidence=parse_confidence(f.get("confidence", 50)),
            evidence=f.get("evidence"),
            analyzer="llm",
        ) for f in data.get("findings", []) if parse_confidence(f.get("confidence", 50)) >= 0.5]

    def _verify(self, finding: Finding, ctx: ReviewContext) -> tuple[bool, float, str]:
        """Independent verification. Returns (verified, confidence, reason)."""
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
