"""Audit logging — track user actions for compliance and debugging."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AuditEvent:
    user: str
    action: str
    resource: str
    details: str = ""
    timestamp: str = ""


class AuditLogger:
    def __init__(self, path: str = ".ai-pr-reviewer/audit.jsonl"):
        self._path = Path(path)

    def log(self, user: str, action: str, resource: str, details: str = ""):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        event = AuditEvent(
            user=user, action=action, resource=resource,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")

    def get_trail(self, resource: str = "", limit: int = 100) -> list[AuditEvent]:
        if not self._path.exists():
            return []
        events = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if not resource or resource in data.get("resource", ""):
                            events.append(AuditEvent(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return events[-limit:]


VALID_ACTIONS = [
    "review_started", "review_completed", "finding_published",
    "feedback_marked", "fix_applied", "config_changed",
    "user_invited", "repo_connected",
]
