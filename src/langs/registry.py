from src.langs.base import LanguageSupport

_LANGUAGES: dict[str, LanguageSupport] = {}


def _register(lang: LanguageSupport):
    _LANGUAGES[lang.name] = lang


_register(LanguageSupport(
    name="python",
    extensions=[".py", ".pyw"],
    sast_tool="bandit",
    prompt_hints=(
        "Python-specific: check for None handling, context managers, "
        "async/await correctness, f-string safety, pickle/exec/eval usage."
    ),
))

_register(LanguageSupport(
    name="javascript",
    extensions=[".js", ".mjs", ".cjs", ".jsx"],
    sast_tool="eslint",
    prompt_hints=(
        "JavaScript-specific: check for prototype pollution, "
        "== vs ===, async error handling, XSS via innerHTML, eval usage."
    ),
))

_register(LanguageSupport(
    name="typescript",
    extensions=[".ts", ".tsx", ".mts", ".cts", ".d.ts"],
    sast_tool="eslint",
    prompt_hints=(
        "TypeScript-specific: check type assertions (as / !), "
        "any usage, strict null checks bypass, unsafe type casts."
    ),
))

_register(LanguageSupport(
    name="go",
    extensions=[".go"],
    sast_tool="staticcheck",
    prompt_hints=(
        "Go-specific: check error handling (ignored err), "
        "goroutine leaks, defer in loops, nil pointer dereference."
    ),
))

SUPPORTED_EXTENSIONS = {
    ext for lang in _LANGUAGES.values() for ext in lang.extensions
}


def detect_language(path: str) -> str:
    for lang_name, lang in _LANGUAGES.items():
        if lang.matches(path):
            return lang_name
    return "text"


def get_lang(name: str) -> LanguageSupport | None:
    return _LANGUAGES.get(name)
