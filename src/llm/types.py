from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    model: str = "unknown"
    provider: str = "unknown"
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
