"""In-memory evidence graph with bounded, auditable traversal."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from app.graph.models import GraphEdge, GraphNode, NodeType, RelationType
from app.utils.text import tokenize


class EvidenceGraph:
    """Graph of derived intelligence nodes whose provenance resolves to events."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)

    def add_node(self, node: GraphNode) -> GraphNode:
        existing = self._nodes.get(node.id)
        if existing is None:
            self._nodes[node.id] = node
            return node
        existing.evidence_ids.update(node.evidence_ids)
        existing.aliases.update(node.aliases)
        existing.attributes.update(node.attributes)
        return existing

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            raise KeyError("both graph edge endpoints must exist")
        if any(existing.id == edge.id for existing in self._outgoing[edge.source_id]):
            return
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)

    def get(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def nodes(self, node_type: NodeType | None = None) -> list[GraphNode]:
        values = list(self._nodes.values())
        return values if node_type is None else [node for node in values if node.node_type is node_type]

    def edges(self) -> list[GraphEdge]:
        return [edge for edges in self._outgoing.values() for edge in edges]

    def adjacent(
        self,
        node_id: str,
        relations: set[RelationType] | None = None,
        *,
        direction: str = "both",
    ) -> list[tuple[GraphEdge, GraphNode]]:
        pairs: list[tuple[GraphEdge, GraphNode]] = []
        if direction in {"out", "both"}:
            pairs.extend(
                (edge, self._nodes[edge.target_id])
                for edge in self._outgoing.get(node_id, [])
                if relations is None or edge.relation in relations
            )
        if direction in {"in", "both"}:
            pairs.extend(
                (edge, self._nodes[edge.source_id])
                for edge in self._incoming.get(node_id, [])
                if relations is None or edge.relation in relations
            )
        return pairs

    def expand(
        self,
        seed_ids: Iterable[str],
        *,
        max_hops: int = 2,
        relations: set[RelationType] | None = None,
        max_nodes: int = 250,
    ) -> tuple[set[str], dict[str, list[str]]]:
        """Return reached nodes and the relation path that first reached each node."""

        reached = {node_id for node_id in seed_ids if node_id in self._nodes}
        paths = {node_id: [] for node_id in reached}
        queue = deque((node_id, 0) for node_id in reached)
        while queue and len(reached) < max_nodes:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for edge, neighbor in self.adjacent(current, relations):
                if neighbor.id in reached:
                    continue
                reached.add(neighbor.id)
                paths[neighbor.id] = paths[current] + [edge.id]
                queue.append((neighbor.id, depth + 1))
                if len(reached) >= max_nodes:
                    break
        return reached, paths

    def find_entities(self, query: str, limit: int = 12) -> list[GraphNode]:
        query_terms = set(tokenize(query, remove_stopwords=True))
        scored: list[tuple[float, GraphNode]] = []
        for node in self._nodes.values():
            if node.node_type is NodeType.EVENT:
                continue
            terms = set(tokenize(" ".join([node.label, *node.aliases]), remove_stopwords=True))
            if not terms or not query_terms:
                continue
            overlap = len(query_terms & terms) / len(terms)
            if overlap:
                scored.append((overlap, node))
        return [node for _, node in sorted(scored, key=lambda item: (-item[0], item[1].id))[:limit]]

    def evidence_ids(self, node_ids: Iterable[str]) -> set[str]:
        evidence: set[str] = set()
        for node_id in node_ids:
            node = self._nodes.get(node_id)
            if node:
                evidence.update(node.evidence_ids)
        return evidence

    def communities(self, minimum_size: int = 2) -> list[set[str]]:
        """Return deterministic connected components for inspectable community discovery."""

        unvisited = set(self._nodes)
        communities: list[set[str]] = []
        while unvisited:
            seed = min(unvisited)
            component, _ = self.expand([seed], max_hops=100, max_nodes=len(self._nodes))
            unvisited -= component
            if len(component) >= minimum_size:
                communities.append(component)
        return sorted(communities, key=lambda values: (-len(values), min(values)))

