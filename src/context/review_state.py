import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewState:
    """Track which PR commits have been reviewed to avoid duplicate reviews."""

    def __init__(self, path: str = ".ai-pr-reviewer/state.json"):
        self._path = Path(path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8")
            if not text.strip():
                return {}
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def is_reviewed(self, pr_number: int, head_sha: str) -> bool:
        pr_key = str(pr_number)
        return self._data.get(pr_key, {}).get("sha") == head_sha

    def last_reviewed_sha(self, pr_number: int) -> str | None:
        pr_key = str(pr_number)
        entry = self._data.get(pr_key)
        return entry["sha"] if entry else None

    def mark_reviewed(self, pr_number: int, head_sha: str,
                      findings_count: int = 0):
        pr_key = str(pr_number)
        self._data[pr_key] = {
            "sha": head_sha,
            "findings": findings_count,
            "reviewed_at": _now_iso(),
        }
        self._save()
