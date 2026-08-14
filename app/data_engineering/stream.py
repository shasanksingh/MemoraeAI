"""Small stream abstraction used locally and replaceable by a durable broker."""

from __future__ import annotations

from collections import deque

from app.data_engineering.models import EventEnvelope


class InMemoryEventStream:
    def __init__(self) -> None:
        self._queue: deque[EventEnvelope] = deque()

    def publish(self, envelope: EventEnvelope) -> None:
        self._queue.append(envelope)

    def consume(self, maximum: int = 100) -> list[EventEnvelope]:
        return [self._queue.popleft() for _ in range(min(maximum, len(self._queue)))]

    def __len__(self) -> int:
        return len(self._queue)

