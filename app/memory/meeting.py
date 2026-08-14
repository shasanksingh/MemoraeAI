"""Meeting memory for discussions, deadlines, and meeting evolution."""

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType


class MeetingMemory:
    def __init__(self, graph: EvidenceGraph) -> None:
        self._meetings = graph.nodes(NodeType.MEETING)

    def all(self) -> list[GraphNode]:
        return list(self._meetings)

