"""Relationship memory derived from evidence-backed graph connections."""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.evidence import EvidenceGraph
from app.graph.models import NodeType


@dataclass(frozen=True, slots=True)
class Relationship:
    entity_id: str
    name: str
    event_ids: tuple[str, ...]
    connection_count: int


class RelationshipMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._relationships = [
            Relationship(node.id, node.label, tuple(sorted(node.evidence_ids)), len(graph.adjacent(node.id)))
            for node in graph.nodes(NodeType.PERSON)
        ]

    def all(self) -> list[Relationship]:
        return sorted(self._relationships, key=lambda item: (-item.connection_count, item.name))

