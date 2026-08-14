"""Evidence-driven selection of memory projections for expansion."""

from __future__ import annotations

from app.graph.evidence import EvidenceGraph
from app.graph.models import NodeType


class MemoryRouter:
    """Select projections only after seed evidence reveals relevant node types."""

    _layers = {
        NodeType.EVENT: {"episodic"},
        NodeType.PERSON: {"relationship", "interaction"},
        NodeType.PROJECT: {"project", "semantic"},
        NodeType.TASK: {"commitment", "activity"},
        NodeType.MEETING: {"temporal_event", "interaction"},
        NodeType.DECISION: {"semantic", "activity"},
        NodeType.DEADLINE: {"commitment", "temporal_event"},
        NodeType.RISK: {"commitment", "activity"},
        NodeType.DEPENDENCY: {"commitment", "relationship"},
        NodeType.PREFERENCE: {"preference"},
        NodeType.ACTIVITY: {"activity"},
        NodeType.GOAL: {"goal", "activity"},
        NodeType.LEARNING: {"learning", "semantic"},
        NodeType.TOPIC: {"semantic", "project"},
    }

    def select(self, graph: EvidenceGraph, node_ids: set[str]) -> tuple[str, ...]:
        layers = {"episodic"}
        for node_id in node_ids:
            node = graph.get(node_id)
            if node:
                layers.update(self._layers.get(node.node_type, set()))
        return tuple(sorted(layers))
