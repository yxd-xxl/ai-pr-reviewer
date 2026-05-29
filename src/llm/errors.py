class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMJSONParseError(LLMError):
    def __init__(self, raw: str, msg: str = ""):
        self.raw = raw
        super().__init__(f"JSON parse failed: {msg}" if msg else "JSON parse failed")


class LLMRateLimitError(LLMError):
    pass
