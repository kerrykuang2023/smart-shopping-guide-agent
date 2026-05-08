from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Iterable

from app.models import ActivityLogEntry


class ActivityLogService:
    def __init__(self, max_entries: int = 500) -> None:
        self._entries: deque[ActivityLogEntry] = deque(maxlen=max_entries)

    def add(self, entry: ActivityLogEntry) -> None:
        self._entries.appendleft(entry)

    def recent(self, limit: int = 100) -> list[ActivityLogEntry]:
        return list(self._entries)[:limit]

    def seed_startup(self) -> None:
        self.add(
            ActivityLogEntry(
                timestamp=datetime.utcnow(),
                action="system_startup",
                details={"message": "Backend service started"},
            )
        )

    def __len__(self) -> int:
        return len(self._entries)

    def iter_entries(self) -> Iterable[ActivityLogEntry]:
        return iter(self._entries)

