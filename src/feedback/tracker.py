"""FP/TP feedback tracking and confidence adjustment."""

import json
import hashlib
from pathlib import Path

_DEFAULT_PATH = ".ai-pr-reviewer/feedback.json"


def fingerprint(finding) -> str:
    """Generate stable fingerprint for a finding."""
    key = f"{finding.location.file}:{finding.location.line}:{finding.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class FeedbackTracker:
    def __init__(self, path: str = _DEFAULT_PATH):
        self._path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {"false_positives": {}, "true_positives": {}}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"false_positives": {}, "true_positives": {}}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def mark_fp(self, finding, user: str = "unknown"):
        fp_key = fingerprint(finding)
        self._data["false_positives"][fp_key] = {
            "title": finding.title,
            "file": finding.location.file,
            "category": finding.category,
            "marked_by": user,
            "count": self._data["false_positives"].get(fp_key, {}).get("count", 0) + 1,
        }
        self._save()

    def mark_tp(self, finding, user: str = "unknown"):
        tp_key = fingerprint(finding)
        self._data["true_positives"][tp_key] = {
            "title": finding.title,
            "file": finding.location.file,
            "category": finding.category,
            "marked_by": user,
            "count": self._data["true_positives"].get(tp_key, {}).get("count", 0) + 1,
        }
        self._save()

    def is_known_fp(self, finding) -> bool:
        return fingerprint(finding) in self._data["false_positives"]

    def fp_count(self, finding) -> int:
        return self._data["false_positives"].get(fingerprint(finding), {}).get("count", 0)
