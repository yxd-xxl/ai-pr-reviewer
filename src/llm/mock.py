from src.llm.interface import LLMAdapter
from src.llm.types import LLMResponse


class MockLLMAdapter(LLMAdapter):
    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        return LLMResponse(
            content="[mock] This is a mock review response. No real LLM was called.",
            model="mock", provider="mock", latency_ms=1,
        )

    def complete_json(self, *, system: str, user: str,
                      schema: type | None = None, temperature: float = 0.0) -> dict:
        return {
            "findings": [
                {
                    "severity": "medium",
                    "category": "style",
                    "title": "Mock finding",
                    "description": "This is a mock finding.",
                    "suggestion": "Enable a real LLM provider.",
                    "line": 1,
                    "evidence": "Mock diff analysis",
                    "classification": "new",
                    "confidence": 75,
                }
            ]
        }
