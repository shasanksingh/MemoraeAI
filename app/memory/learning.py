"""Learning memory for lessons, realizations, and durable takeaways."""

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class LearningMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._learnings = graph.nodes(NodeType.LEARNING)

    def all(self) -> list[GraphNode]:
        return list(self._learnings)

