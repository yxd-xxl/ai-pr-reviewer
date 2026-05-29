import pytest
from src.llm import (
    LLMAdapter, LLMResponse, LLMError, LLMTimeoutError,
    LLMJSONParseError, MockLLMAdapter, create_adapter,
)


class TestLLMResponse:
    def test_defaults(self):
        r = LLMResponse(content="ok")
        assert r.content == "ok"
        assert r.model == "unknown"
        assert r.provider == "unknown"
        assert r.usage == {}
        assert r.latency_ms == 0  # default: not measured

    def test_full_fields(self):
        r = LLMResponse(content="ok", model="gpt", provider="openai",
                        usage={"tokens": 100}, latency_ms=500)
        assert r.model == "gpt"
        assert r.provider == "openai"
        assert r.usage == {"tokens": 100}
        assert r.latency_ms == 500


class TestMockLLMAdapter:
    def test_complete_returns_fixed_response(self):
        adapter = MockLLMAdapter()
        resp = adapter.complete(system="You are a reviewer", user="Review this code")
        assert isinstance(resp, LLMResponse)
        assert "mock" in resp.content.lower()
        assert resp.provider == "mock"
        assert resp.model == "mock"

    def test_complete_json_returns_dict(self):
        adapter = MockLLMAdapter()
        resp = adapter.complete_json(system="s", user="u")
        assert isinstance(resp, dict)
        assert "findings" in resp
        assert resp["findings"][0]["severity"] == "medium"

    def test_complete_json_with_schema(self):
        adapter = MockLLMAdapter()
        resp = adapter.complete_json(system="s", user="u", schema=dict)
        assert isinstance(resp, dict)


class TestCreateAdapter:
    def test_returns_mock_by_default(self, mocker):
        mocker.patch.dict("os.environ", {}, clear=True)
        adapter = create_adapter()
        assert isinstance(adapter, MockLLMAdapter)

    def test_returns_mock_when_provider_is_mock(self, mocker):
        mocker.patch.dict("os.environ", {"LLM_PROVIDER": "mock"}, clear=True)
        adapter = create_adapter()
        assert isinstance(adapter, MockLLMAdapter)
