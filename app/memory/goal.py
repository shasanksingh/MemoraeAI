"""Goal memory and evidence-linked goal observations."""

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class GoalMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._goals = graph.nodes(NodeType.GOAL)

    def all(self) -> list[GraphNode]:
        return list(self._goals)

