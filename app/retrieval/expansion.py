"""Graph, entity, temporal, project, and dependency evidence expansion."""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.evidence import EvidenceGraph
from app.graph.models import RelationType
from app.memory.models import Event
from app.retrieval.planner import RetrievalPlan


@dataclass(frozen=True, slots=True)
class ExpansionResult:
    event_ids: frozenset[str]
    node_ids: frozenset[str]
    paths: dict[str, list[str]]
    reasons: dict[str, tuple[str, ...]]


class EvidenceDiscoveryEngine:
    """Expand from observed evidence rather than a predefined query route."""

    _dependency_relations = {
        RelationType.DEPENDS_ON,
        RelationType.BLOCKED_BY,
        RelationType.UNBLOCKS,
        RelationType.IMPACTS,
    }

    def __init__(
        self,
        graph: EvidenceGraph,
        events: list[Event],
        temporal_neighbors: int = 3,
        max_events: int = 500,
    ) -> None:
        self.graph = graph
        self.events = sorted(events, key=lambda item: (item.timestamp, item.id))
        self._index = {event.id: position for position, event in enumerate(self.events)}
        self.temporal_neighbors = temporal_neighbors
        self.max_events = max_events

    def expand(self, seed_event_ids: set[str], plan: RetrievalPlan) -> ExpansionResult:
        seed_nodes = {f"event:{event_id}" for event_id in seed_event_ids} | set(plan.entity_seed_ids)
        reached, paths = self.graph.expand(seed_nodes, max_hops=plan.max_hops)
        reasons: dict[str, set[str]] = {}
        for node_id in reached - seed_nodes:
            reasons.setdefault(node_id, set()).add("graph expansion")
        dependency_nodes, dependency_paths = self.graph.expand(
            seed_nodes,
            max_hops=plan.max_hops,
            relations=self._dependency_relations,
            max_nodes=100,
        )
        for node_id in dependency_nodes - seed_nodes:
            reached.add(node_id)
            paths.setdefault(node_id, dependency_paths.get(node_id, []))
            reasons.setdefault(node_id, set()).add("dependency expansion")
        evidence_ids = self.graph.evidence_ids(reached)
        for event_id in seed_event_ids:
            if len(evidence_ids) >= self.max_events:
                break
            position = self._index.get(event_id)
            if position is None:
                continue
            start = max(0, position - self.temporal_neighbors)
            end = min(len(self.events), position + self.temporal_neighbors + 1)
            for neighbor in self.events[start:end]:
                if len(evidence_ids) >= self.max_events:
                    break
                evidence_ids.add(neighbor.id)
                node_id = f"event:{neighbor.id}"
                reached.add(node_id)
                reasons.setdefault(node_id, set()).add("temporal expansion")
                paths.setdefault(node_id, [])
        return ExpansionResult(
            event_ids=frozenset(evidence_ids),
            node_ids=frozenset(reached),
            paths=paths,
            reasons={node_id: tuple(sorted(values)) for node_id, values in reasons.items()},
        )
