"""Immutable episodic memory for normalized raw events."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from app.memory.models import Event


class EpisodicMemory:
    """Point-in-time collection of every ingested raw event."""

    def __init__(self, events: Iterable[Event]) -> None:
        self._events = sorted(events, key=lambda event: (event.timestamp, event.id))
        self._by_id = {event.id: event for event in self._events}

    def all(self) -> list[Event]:
        return list(self._events)

    def get(self, event_id: str) -> Event | None:
        return self._by_id.get(event_id)

    def between(self, start: datetime, end: datetime) -> list[Event]:
        return [event for event in self._events if start <= event.timestamp <= end]

    def by_ids(self, event_ids: Iterable[str]) -> list[Event]:
        return [self._by_id[event_id] for event_id in event_ids if event_id in self._by_id]

    def __len__(self) -> int:
        return len(self._events)
