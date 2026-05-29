from abc import ABC, abstractmethod

from src.llm.types import LLMResponse


class LLMAdapter(ABC):
    @abstractmethod
    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        ...

    @abstractmethod
    def complete_json(self, *, system: str, user: str,
                      schema: type | None = None, temperature: float = 0.0) -> dict:
        ...
