"""Anthropic Claude adapter — Claude Opus 4.7 / Sonnet 4.6."""

import json
import time
import urllib.request
import urllib.error
from src.llm.interface import LLMAdapter
from src.llm.types import LLMResponse
from src.llm.errors import LLMError, LLMTimeoutError, LLMJSONParseError, LLMRateLimitError


class AnthropicAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6",
                 timeout: int = 120, max_retries: int = 2):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        t0 = time.time()
        body = json.dumps({
            "model": self._model, "max_tokens": 4096,
            "system": system, "messages": [{"role": "user", "content": user}],
            "temperature": temperature,
        }).encode()
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._call(body)
                latency = int((time.time() - t0) * 1000)
                content = resp["content"][0]["text"]
                usage = resp.get("usage", {})
                return LLMResponse(content=content, model=self._model,
                                   provider="anthropic", usage=usage, latency_ms=latency)
            except (LLMTimeoutError, LLMRateLimitError):
                if attempt == self._max_retries: raise

    def complete_json(self, *, system: str, user: str, temperature: float = 0.0, **kw) -> dict:
        system = system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."
        resp = self.complete(system=system, user=user, temperature=temperature)
        text = resp.content.strip()
        if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {"findings": []}
        except json.JSONDecodeError as e:
            raise LLMJSONParseError(text, str(e))

    def _call(self, body: bytes) -> dict:
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        })
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: raise LLMRateLimitError(str(e))
            raise LLMError(f"HTTP {e.code}: {e}")
        except TimeoutError:
            raise LLMTimeoutError("Request timed out")
