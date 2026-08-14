"""Evidence-first GraphRAG retrieval orchestration and structured trace."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.graph.evidence import EvidenceGraph
from app.graph.models import NodeType
from app.memory.models import RetrievalHit
from app.retrieval.expansion import EvidenceDiscoveryEngine
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.memory_router import MemoryRouter
from app.retrieval.planner import RetrievalPlan, RetrievalPlanner
from app.utils.text import tokenize


@dataclass(frozen=True, slots=True)
class RetrievalRound:
    round_number: int
    operation: str
    candidate_count: int
    new_event_ids: tuple[str, ...]
    marginal_gain: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "round": self.round_number,
            "operation": self.operation,
            "candidate_count": self.candidate_count,
            "new_event_ids": list(self.new_event_ids),
            "marginal_gain": round(self.marginal_gain, 4),
            "reasons": list(self.reasons),
        }


@dataclass(slots=True)
class GraphRetrievalResult:
    plan: RetrievalPlan
    hits: list[RetrievalHit]
    rounds: list[RetrievalRound]
    selected_memory_layers: tuple[str, ...]
    expansion_paths: dict[str, list[str]] = field(default_factory=dict)
    stop_reason: str = ""

    def trace_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.to_dict(),
            "rounds": [item.to_dict() for item in self.rounds],
            "selected_memory_layers": list(self.selected_memory_layers),
            "expansion_paths": self.expansion_paths,
            "stop_reason": self.stop_reason,
        }


class GraphRAGRetriever:
    """Broad recall, evidence expansion, query-aware reranking, and stopping."""

    def __init__(
        self,
        graph: EvidenceGraph,
        recall: HybridRetriever,
        planner: RetrievalPlanner,
        discovery: EvidenceDiscoveryEngine,
        memory_router: MemoryRouter | None = None,
    ) -> None:
        self.graph = graph
        self.recall = recall
        self.planner = planner
        self.discovery = discovery
        self.memory_router = memory_router or MemoryRouter()

    def _facet_score(self, event_id: str, plan: RetrievalPlan) -> float:
        nodes = [node for node in self.graph.nodes() if event_id in node.evidence_ids]
        score = 0.0
        requested = set(plan.requested_relations)
        if requested:
            for node in nodes:
                for edge, _ in self.graph.adjacent(node.id):
                    if edge.relation in requested:
                        score = max(score, edge.confidence)
        if "priority" in plan.requested_facets:
            for node in nodes:
                if node.node_type is NodeType.TASK:
                    score = max(
                        score,
                        0.4 * float(node.attributes.get("urgency", 0.0))
                        + 0.35 * float(node.attributes.get("risk", 0.0))
                        + 0.25 * float(node.attributes.get("importance", 0.0)),
                    )
        return score

    def _rerank(self, plan: RetrievalPlan, hits: list[RetrievalHit], expanded_ids: set[str]) -> list[RetrievalHit]:
        query_terms = set(plan.query_terms)
        for hit in hits:
            document_terms = set(tokenize(hit.event.content, remove_stopwords=True))
            term_coverage = len(query_terms & document_terms) / max(1, len(query_terms))
            facet = self._facet_score(hit.event.id, plan)
            graph_support = 1.0 if hit.event.id in expanded_ids else 0.0
            hit.score = 0.62 * hit.score + 0.18 * term_coverage + 0.14 * facet + 0.06 * graph_support
        return sorted(hits, key=lambda item: (-item.score, -item.lexical_score, item.event.id))

    def retrieve(self, query: str) -> GraphRetrievalResult:
        plan = self.planner.plan(query, self.graph, self.recall.as_of)
        broad = self.recall.retrieve(query, limit=plan.broad_limit)
        ledger = {hit.event.id: hit for hit in broad}
        rounds = [
            RetrievalRound(0, "parallel sparse/vector broad recall", len(ledger),
                           tuple(hit.event.id for hit in broad), 1.0 if broad else 0.0,
                           ("all queries start from raw evidence recall",))
        ]
        seed_ids = {hit.event.id for hit in broad[: max(plan.final_limit, 12)]}
        all_nodes = {f"event:{event_id}" for event_id in seed_ids} | set(plan.entity_seed_ids)
        expansion_paths: dict[str, list[str]] = {}
        low_gain_rounds = 0
        stop_reason = "maximum expansion rounds reached"
        original_ids = set(ledger)
        for round_number in range(1, plan.max_rounds + 1):
            expansion = self.discovery.expand(seed_ids, plan)
            new_ids = set(expansion.event_ids) - set(ledger)
            ledger.update((hit.event.id, hit) for hit in self.recall.score_events(query, new_ids))
            all_nodes.update(expansion.node_ids)
            expansion_paths.update(expansion.paths)
            marginal_gain = len(new_ids) / max(1, len(ledger))
            reasons = sorted({reason for values in expansion.reasons.values() for reason in values})
            rounds.append(RetrievalRound(round_number, "graph/entity/temporal/dependency expansion",
                                         len(ledger), tuple(sorted(new_ids)), marginal_gain, tuple(reasons)))
            if not new_ids:
                stop_reason = "evidence frontier exhausted"
                break
            low_gain_rounds = low_gain_rounds + 1 if marginal_gain < 0.02 else 0
            if low_gain_rounds >= 2:
                stop_reason = "marginal evidence gain below threshold for two rounds"
                break
            seed_ids = new_ids
        ranked = self._rerank(plan, list(ledger.values()), set(ledger) - original_ids)
        selected = ranked[: plan.final_limit]
        selected_nodes = all_nodes | {f"event:{hit.event.id}" for hit in selected}
        return GraphRetrievalResult(
            plan=plan,
            hits=selected,
            rounds=rounds,
            selected_memory_layers=self.memory_router.select(self.graph, selected_nodes),
            expansion_paths=expansion_paths,
            stop_reason=stop_reason,
        )

