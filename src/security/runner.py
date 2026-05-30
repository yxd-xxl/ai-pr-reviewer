"""Unified SAST dispatcher — routes files to language-specific runners."""

from dataclasses import dataclass, field

from src.langs.registry import detect_language, get_lang
from src.security.bandit_runner import run_bandit
from src.security.eslint_runner import run_eslint
from src.security.staticcheck_runner import run_staticcheck


@dataclass
class SastResult:
    language: str
    findings: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _get_runner(name: str):
    """Look up a SAST runner by tool name. Uses dynamic lookup so that
    tests can patch the module-level imports and have them take effect."""
    _runners = {
        "bandit": run_bandit,
        "eslint": run_eslint,
        "staticcheck": run_staticcheck,
    }
    return _runners.get(name)


def run_sast(file_paths: list[str]) -> dict[str, SastResult]:
    """Run all applicable SAST tools on the given files.
    Returns dict mapping language name to SastResult.
    """
    if not file_paths:
        return {}

    # Group files by language
    by_lang: dict[str, list[str]] = {}
    for path in file_paths:
        lang = detect_language(path)
        if lang == "text":
            continue
        by_lang.setdefault(lang, []).append(path)

    results: dict[str, SastResult] = {}
    for lang, paths in by_lang.items():
        lang_support = get_lang(lang)
        if lang_support is None or lang_support.sast_tool is None:
            continue

        runner = _get_runner(lang_support.sast_tool)
        if runner is None:
            continue

        try:
            findings, warnings = runner(paths)
        except Exception as e:
            findings, warnings = [], [f"SAST runner {lang_support.sast_tool} failed: {e}"]

        results[lang] = SastResult(
            language=lang,
            findings=findings,
            warnings=warnings,
        )

    return results
