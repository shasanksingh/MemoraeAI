"""Decision memory with evidence and graph impact relationships."""

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class DecisionMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._decisions = graph.nodes(NodeType.DECISION)

    def all(self) -> list[GraphNode]:
        return list(self._decisions)

