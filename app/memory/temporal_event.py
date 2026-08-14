"""Temporal-event memory for timeline reconstruction."""

from __future__ import annotations

from datetime import datetime

from app.memory.models import Event


class TemporalEventMemory:
    def __init__(self, events: list[Event]) -> None:
        self._events = sorted(events, key=lambda event: (event.timestamp, event.id))

    def around(self, timestamp: datetime, *, before: int = 3, after: int = 3) -> list[Event]:
        if not self._events:
            return []
        index = min(range(len(self._events)), key=lambda value: abs((self._events[value].timestamp - timestamp).total_seconds()))
        return self._events[max(0, index - before): index + after + 1]

    def all(self) -> list[Event]:
        return list(self._events)

