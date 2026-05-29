import os

from src.llm.interface import LLMAdapter
from src.llm.mock import MockLLMAdapter
from src.llm.deepseek import DeepSeekAdapter
from src.llm.errors import LLMError


def create_adapter() -> LLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider == "mock":
        return MockLLMAdapter()
    elif provider in ("deepseek", "anthropic", "openai"):
        api_key = os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL", "")
        model = os.getenv("LLM_MODEL", "")
        timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
        max_retries = int(os.getenv("MAX_RETRIES", "2"))
        if not api_key:
            raise LLMError(f"LLM_API_KEY not set for provider '{provider}'")
        return DeepSeekAdapter(
            api_key=api_key, base_url=base_url, model=model,
            timeout=timeout, max_retries=max_retries,
        )
    else:
        raise LLMError(f"Unknown LLM_PROVIDER: {provider}")
