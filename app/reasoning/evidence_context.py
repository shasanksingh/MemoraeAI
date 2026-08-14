"""Coverage-aware context assembly from a query-local evidence graph."""

from __future__ import annotations

from app.graph.evidence import EvidenceGraph
from app.memory.models import RetrievalHit
from app.reasoning.context import ContextStats
from app.reasoning.context_quality import ContextQuality, ContextQualityScorer
from app.retrieval.graphrag import GraphRetrievalResult
from app.utils.text import estimate_tokens, jaccard, tokenize


class EvidenceContextAssembler:
    """Select diverse evidence while preserving corrections and graph provenance."""

    def __init__(
        self,
        graph: EvidenceGraph,
        *,
        token_budget: int = 4_000,
        near_duplicate_threshold: float = 0.88,
        quality_scorer: ContextQualityScorer | None = None,
    ) -> None:
        self.graph = graph
        self.token_budget = token_budget
        self.near_duplicate_threshold = near_duplicate_threshold
        self.quality_scorer = quality_scorer or ContextQualityScorer()

    def _utility(self, hit: RetrievalHit, selected: list[RetrievalHit], query_terms: set[str]) -> float:
        terms = set(tokenize(hit.event.content, remove_stopwords=True))
        coverage = len(query_terms & terms) / max(1, len(query_terms))
        source_novelty = 1.0 if hit.event.source not in {item.event.source for item in selected} else 0.0
        redundancy = max((jaccard(hit.event.content, item.event.content) for item in selected), default=0.0)
        return 0.60 * hit.score + 0.24 * coverage + 0.10 * source_novelty - 0.18 * redundancy

    def assemble(
        self,
        result: GraphRetrievalResult,
    ) -> tuple[list[RetrievalHit], list[dict[str, object]], ContextStats, ContextQuality]:
        stats = ContextStats(input_count=len(result.hits))
        selected: list[RetrievalHit] = []
        remaining = list(result.hits)
        tokens = 0
        query_terms = set(result.plan.query_terms)
        while remaining:
            hit = max(remaining, key=lambda item: self._utility(item, selected, query_terms))
            remaining.remove(hit)
            if any(jaccard(hit.event.content, item.event.content) >= self.near_duplicate_threshold for item in selected):
                stats.duplicates_removed += 1
                continue
            cost = estimate_tokens(hit.event.content) + 32
            if tokens + cost > self.token_budget:
                stats.budget_omissions += 1
                continue
            selected.append(hit)
            tokens += cost
        stats.tokens_used = tokens

        context: list[dict[str, object]] = []
        for hit in selected:
            linked_nodes = [
                node for node in self.graph.nodes()
                if hit.event.id in node.evidence_ids and node.id != f"event:{hit.event.id}"
            ]
            item = hit.to_dict()
            event_node_id = f"event:{hit.event.id}"
            relations_out = {edge.relation.value for edge, _ in self.graph.adjacent(event_node_id, direction="out")}
            relations_in = {edge.relation.value for edge, _ in self.graph.adjacent(event_node_id, direction="in")}
            if "supersedes" in relations_out:
                evidence_role = "correction"
            elif "supersedes" in relations_in:
                evidence_role = "historical"
            else:
                evidence_role = "current_support"
            item["evidence_graph"] = {
                "evidence_role": evidence_role,
                "nodes": [node.to_dict() for node in linked_nodes],
                "expansion_paths": {
                    node.id: result.expansion_paths.get(node.id, [])
                    for node in linked_nodes
                    if node.id in result.expansion_paths
                },
            }
            context.append(item)
        quality = self.quality_scorer.score(result.plan, selected, self.graph)
        return selected, context, stats, quality
