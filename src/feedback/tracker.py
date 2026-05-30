"""FP/TP feedback tracking — multi-state with persistence."""

import json
import hashlib
from enum import Enum
from pathlib import Path

_DEFAULT_PATH = ".ai-pr-reviewer/feedback.json"


class FeedbackState(str, Enum):
    UNMARKED = "unmarked"
    TRUE_POSITIVE = "tp"
    FALSE_POSITIVE = "fp"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"
    LOW_PRIORITY = "low_pri"
    NEEDS_DISCUSSION = "discuss"
    FIXED = "fixed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


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
            return {"entries": {}}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if "entries" not in data:
                # Migrate old format: {"false_positives": {...}, "true_positives": {...}}
                data = self._migrate_old_format(data)
            return data
        except (json.JSONDecodeError, OSError):
            return {"entries": {}}

    def _migrate_old_format(self, data: dict) -> dict:
        entries = {}
        for fp_key, fp_data in data.get("false_positives", {}).items():
            entries[fp_key] = {
                "state": FeedbackState.FALSE_POSITIVE.value,
                "title": fp_data.get("title", ""),
                "file": fp_data.get("file", ""),
                "category": fp_data.get("category", ""),
                "marked_by": fp_data.get("marked_by", "unknown"),
                "reason": "",
                "count": fp_data.get("count", 1),
            }
        for tp_key, tp_data in data.get("true_positives", {}).items():
            entries[tp_key] = {
                "state": FeedbackState.TRUE_POSITIVE.value,
                "title": tp_data.get("title", ""),
                "file": tp_data.get("file", ""),
                "category": tp_data.get("category", ""),
                "marked_by": tp_data.get("marked_by", "unknown"),
                "reason": "",
                "count": tp_data.get("count", 1),
            }
        return {"entries": entries}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def mark(self, finding, state: FeedbackState | str,
             user: str = "unknown", reason: str = ""):
        fp_key = fingerprint(finding)
        state_val = state.value if isinstance(state, FeedbackState) else state
        existing = self._data["entries"].get(fp_key, {})
        self._data["entries"][fp_key] = {
            "state": state_val,
            "title": finding.title,
            "file": finding.location.file,
            "category": finding.category,
            "marked_by": user,
            "reason": reason,
            "count": existing.get("count", 0) + 1,
        }
        self._save()

    def mark_fp(self, finding, user: str = "unknown"):
        """Legacy API — mark as false positive."""
        self.mark(finding, FeedbackState.FALSE_POSITIVE, user, "Legacy FP mark")

    def mark_tp(self, finding, user: str = "unknown"):
        """Legacy API — mark as true positive."""
        self.mark(finding, FeedbackState.TRUE_POSITIVE, user, "Legacy TP mark")

    def get_state(self, finding) -> FeedbackState:
        fp_key = fingerprint(finding)
        entry = self._data["entries"].get(fp_key, {})
        raw = entry.get("state", "unmarked")
        try:
            return FeedbackState(raw)
        except ValueError:
            return FeedbackState.UNMARKED

    def is_known_fp(self, finding) -> bool:
        return self.get_state(finding) == FeedbackState.FALSE_POSITIVE

    def fp_count(self, finding) -> int:
        fp_key = fingerprint(finding)
        return self._data["entries"].get(fp_key, {}).get("count", 0)
