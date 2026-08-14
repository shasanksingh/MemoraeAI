"""Transparent quality scoring for assembled evidence context."""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.evidence import EvidenceGraph
from app.memory.models import RetrievalHit
from app.retrieval.planner import RetrievalPlan
from app.utils.text import tokenize


@dataclass(frozen=True, slots=True)
class ContextQuality:
    score: float
    evidence_coverage: float
    diversity: float
    recency: float
    completeness: float
    contradiction_resolution: float

    def to_dict(self) -> dict[str, float]:
        return {
            "score": round(self.score, 4),
            "evidence_coverage": round(self.evidence_coverage, 4),
            "diversity": round(self.diversity, 4),
            "recency": round(self.recency, 4),
            "completeness": round(self.completeness, 4),
            "contradiction_resolution": round(self.contradiction_resolution, 4),
        }


class ContextQualityScorer:
    """Score context coverage, diversity, freshness, completeness, and conflicts."""

    _correction_terms = {"correction", "updated", "moved", "ignore", "instead", "not"}

    def score(self, plan: RetrievalPlan, hits: list[RetrievalHit], graph: EvidenceGraph) -> ContextQuality:
        query_terms = set(plan.query_terms)
        covered = set().union(
            *(set(tokenize(hit.event.content, remove_stopwords=True)) for hit in hits)
        ) if hits else set()
        evidence_coverage = len(query_terms & covered) / max(1, len(query_terms))
        sources = {hit.event.source for hit in hits}
        diversity = min(1.0, len(sources) / max(1.0, min(5, len(hits))))
        recency = sum(hit.recency_score for hit in hits) / max(1, len(hits))
        target = plan.final_limit if plan.completeness == "exhaustive" else min(8, plan.final_limit)
        completeness = min(1.0, len(hits) / max(1, target))
        correction_hits = [
            hit for hit in hits
            if set(tokenize(hit.event.content, remove_stopwords=True)) & self._correction_terms
        ]
        if not correction_hits:
            contradiction_resolution = 1.0
        else:
            linked = sum(
                bool(graph.adjacent(f"event:{hit.event.id}"))
                for hit in correction_hits
            )
            contradiction_resolution = linked / len(correction_hits)
        score = (
            0.34 * evidence_coverage
            + 0.18 * diversity
            + 0.10 * recency
            + 0.20 * completeness
            + 0.18 * contradiction_resolution
        )
        return ContextQuality(
            score,
            evidence_coverage,
            diversity,
            recency,
            completeness,
            contradiction_resolution,
        )

