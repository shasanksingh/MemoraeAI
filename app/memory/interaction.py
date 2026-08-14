"""Interaction memory grouped by source and linked people."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.graph.evidence import EvidenceGraph
from app.graph.models import NodeType
from app.memory.models import Event


@dataclass(frozen=True, slots=True)
class InteractionThread:
    key: str
    source: str
    participant_ids: tuple[str, ...]
    event_ids: tuple[str, ...]


class InteractionMemory:
    def __init__(self, events: list[Event], graph: EvidenceGraph) -> None:
        groups: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
        for event in events:
            people = tuple(
                sorted(
                    node.id
                    for _, node in graph.adjacent(f"event:{event.id}")
                    if node.node_type is NodeType.PERSON
                )
            )
            groups[(event.source, people)].append(event.id)
        self._threads = [
            InteractionThread(f"{source}:{'|'.join(people) or 'unknown'}", source, people, tuple(ids))
            for (source, people), ids in groups.items()
        ]

    def all(self) -> list[InteractionThread]:
        return sorted(self._threads, key=lambda item: (-len(item.event_ids), item.key))

