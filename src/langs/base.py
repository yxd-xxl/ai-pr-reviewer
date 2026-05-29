from dataclasses import dataclass


@dataclass
class LanguageSupport:
    name: str
    extensions: list[str]
    sast_tool: str | None = None
    prompt_hints: str = ""

    def matches(self, path: str) -> bool:
        return any(path.endswith(ext) for ext in self.extensions)
