"""Preference memory with raw-event provenance."""

from __future__ import annotations

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class PreferenceMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._items = graph.nodes(NodeType.PREFERENCE)

    def all(self) -> list[GraphNode]:
        return list(self._items)

