"""Activity memory for tasks, meetings, decisions, and risk observations."""

from __future__ import annotations

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class ActivityMemory:
    TYPES = {NodeType.TASK, NodeType.MEETING, NodeType.DECISION, NodeType.RISK, NodeType.ACTIVITY}

    def __init__(self, graph: EvidenceGraph) -> None:
        self._activities = [node for node in graph.nodes() if node.node_type in self.TYPES]

    def all(self) -> list[GraphNode]:
        return list(self._activities)

