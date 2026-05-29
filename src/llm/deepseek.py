import json
import time
import urllib.request
import urllib.error

from src.llm.interface import LLMAdapter
from src.llm.types import LLMResponse
from src.llm.errors import LLMError, LLMTimeoutError, LLMJSONParseError, LLMRateLimitError


class DeepSeekAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str, model: str,
                 timeout: int = 120, max_retries: int = 2):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        t0 = time.time()
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._call_api(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    response_format=None,
                )
                latency = int((time.time() - t0) * 1000)
                content = resp["choices"][0]["message"]["content"]
                usage = resp.get("usage", {})
                return LLMResponse(content=content, model=self._model,
                                   provider="deepseek", usage=usage, latency_ms=latency)
            except (LLMTimeoutError, LLMRateLimitError):
                if attempt == self._max_retries:
                    raise

    def complete_json(self, *, system: str, user: str,
                      schema: type | None = None, temperature: float = 0.0) -> dict:
        t0 = time.time()
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._call_api(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                content = resp["choices"][0]["message"]["content"]
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise LLMJSONParseError(content, str(e))
                if not isinstance(data, dict):
                    raise LLMJSONParseError(content, "Expected JSON object")
                return data
            except (LLMTimeoutError, LLMRateLimitError, LLMJSONParseError):
                if attempt == self._max_retries:
                    raise

    def _call_api(self, messages: list[dict], temperature: float,
                  response_format: dict | None) -> dict:
        body = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            **({"response_format": response_format} if response_format else {}),
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise LLMRateLimitError(f"Rate limited: {e}")
            raise LLMError(f"HTTP {e.code}: {e}")
        except TimeoutError:
            raise LLMTimeoutError("Request timed out")
