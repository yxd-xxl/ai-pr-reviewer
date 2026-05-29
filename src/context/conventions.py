import urllib.request
import json

from src.core.types import ProjectConvention

_SOURCES = [
    ".claude/CLAUDE.md",
]

_MAX_LENGTH = 2000


def load_conventions(token: str, owner: str, repo: str,
                     ref: str = "main") -> list[ProjectConvention]:
    conventions: list[ProjectConvention] = []
    for path in _SOURCES:
        content = _fetch_file(token, owner, repo, path, ref)
        if content:
            truncated = content[:_MAX_LENGTH]
            if len(content) > _MAX_LENGTH:
                truncated += "\n... (truncated)"
            source_type = "coding_style" if "CLAUDE" in path.upper() else "project_doc"
            conventions.append(ProjectConvention(
                source=path, type=source_type, content=truncated,
            ))
    return conventions


def fetch_file_content(token: str, owner: str, repo: str, path: str,
                       ref: str = "main") -> str | None:
    """Fetch full file content from GitHub. For PR analysis context."""
    return _fetch_file(token, owner, repo, path, ref)


def _fetch_file(token: str, owner: str, repo: str, path: str,
                ref: str) -> str | None:
    url = (f"https://api.github.com/repos/{owner}/{repo}"
           f"/contents/{path}?ref={ref}")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None
