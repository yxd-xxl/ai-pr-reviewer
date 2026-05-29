import pytest
from src.langs.registry import get_lang, detect_language, SUPPORTED_EXTENSIONS


class TestDetectLanguage:
    def test_python_extensions(self):
        assert detect_language("src/app.py") == "python"
        assert detect_language("tests/test.py") == "python"

    def test_javascript_extensions(self):
        assert detect_language("src/app.js") == "javascript"
        assert detect_language("lib/util.mjs") == "javascript"

    def test_typescript_extensions(self):
        assert detect_language("src/app.ts") == "typescript"
        assert detect_language("src/types.d.ts") == "typescript"

    def test_go_extension(self):
        assert detect_language("main.go") == "go"

    def test_unknown_extension(self):
        assert detect_language("README.md") == "text"
        assert detect_language("Dockerfile") == "text"


class TestGetLang:
    def test_returns_python_support(self):
        support = get_lang("python")
        assert support is not None
        assert support.sast_tool == "bandit"

    def test_returns_js_support(self):
        support = get_lang("javascript")
        assert support is not None
        assert support.sast_tool == "eslint"

    def test_returns_ts_support(self):
        support = get_lang("typescript")
        assert support is not None
        assert support.sast_tool == "eslint"

    def test_unknown_lang_returns_none(self):
        assert get_lang("text") is None


class TestSupportedExtensions:
    def test_includes_python_js_ts_go(self):
        exts = SUPPORTED_EXTENSIONS
        assert ".py" in exts
        assert ".js" in exts
        assert ".ts" in exts
        assert ".go" in exts
