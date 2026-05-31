import os

from src.llm.interface import LLMAdapter
from src.llm.mock import MockLLMAdapter
from src.llm.deepseek import DeepSeekAdapter
from src.llm.anthropic import AnthropicAdapter
from src.llm.openai import OpenAIAdapter
from src.llm.errors import LLMError


def create_adapter() -> LLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "mock")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
    max_retries = int(os.getenv("MAX_RETRIES", "2"))

    if provider == "mock":
        return MockLLMAdapter()

    if not api_key:
        raise LLMError(f"LLM_API_KEY not set for provider '{provider}'")

    if provider == "deepseek":
        base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        model = model or "deepseek-chat"
        return DeepSeekAdapter(api_key=api_key, base_url=base_url, model=model,
                               timeout=timeout, max_retries=max_retries)

    if provider == "anthropic":
        model = model or "claude-sonnet-4-6"
        return AnthropicAdapter(api_key=api_key, model=model,
                                timeout=timeout, max_retries=max_retries)

    if provider == "openai":
        model = model or "gpt-4o"
        return OpenAIAdapter(api_key=api_key, model=model,
                             timeout=timeout, max_retries=max_retries)

    raise LLMError(f"Unknown LLM_PROVIDER: {provider}. Use: mock, deepseek, anthropic, openai")
