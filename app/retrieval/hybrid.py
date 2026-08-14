"""Broad sparse and lightweight-vector recall for evidence discovery."""

from __future__ import annotations

from datetime import datetime

from app.memory.models import Event, RetrievalHit
from app.retrieval.bm25 import BM25Index
from app.retrieval.embeddings import Embedder, cosine_similarity
from app.utils.time import recency_score


class HybridRetriever:
    """Produce broad candidates without assuming an answer location."""

    def __init__(self, events: list[Event], embedder: Embedder, as_of: datetime, candidate_pool: int = 80) -> None:
        self.events = events
        self._by_id = {event.id: event for event in events}
        self.embedder = embedder
        self.as_of = as_of
        self.candidate_pool = candidate_pool
        self.bm25 = BM25Index(events)
        self._vectors = embedder.encode([event.content for event in events]) if events else []
        self._vector_by_id = {event.id: vector for event, vector in zip(events, self._vectors, strict=True)}

    def _signals(self, query: str) -> tuple[dict[str, float], dict[str, float]]:
        lexical = self.bm25.search(query, self.candidate_pool)
        lexical_map = {event_id: score for event_id, score in lexical}
        max_lexical = max(lexical_map.values(), default=1.0)
        lexical_map = {event_id: score / max_lexical for event_id, score in lexical_map.items()}
        query_vector = self.embedder.encode([query])[0]
        semantic_map = {
            event_id: max(0.0, cosine_similarity(query_vector, vector))
            for event_id, vector in self._vector_by_id.items()
        }
        return lexical_map, semantic_map

    def _hit(self, event: Event, lexical: float, semantic: float) -> RetrievalHit:
        recent = recency_score(event.timestamp, self.as_of)
        relevance = 0.54 * semantic + 0.36 * lexical
        evidence_prior = 0.04 * event.signals.importance_score + 0.03 * event.signals.source_confidence
        freshness_tiebreak = 0.03 * recent
        return RetrievalHit(
            event=event,
            score=relevance + evidence_prior + freshness_tiebreak,
            semantic_similarity=semantic,
            lexical_score=lexical,
            recency_score=recent,
            importance_score=event.signals.importance_score,
            source_confidence=event.signals.source_confidence,
        )

    def retrieve(self, query: str, limit: int = 16) -> list[RetrievalHit]:
        if not self.events:
            return []
        lexical_map, semantic_map = self._signals(query)
        semantic_candidates = sorted(semantic_map, key=lambda event_id: (-semantic_map[event_id], event_id))[
            : self.candidate_pool
        ]
        candidate_ids = set(lexical_map) | set(semantic_candidates)
        hits = [
            self._hit(self._by_id[event_id], lexical_map.get(event_id, 0.0), semantic_map.get(event_id, 0.0))
            for event_id in candidate_ids
        ]
        return sorted(
            hits,
            key=lambda hit: (-hit.score, -hit.lexical_score, -hit.semantic_similarity, hit.event.id),
        )[:limit]

    def score_events(self, query: str, event_ids: set[str]) -> list[RetrievalHit]:
        """Score graph-expanded events using the same transparent features."""

        lexical_map, semantic_map = self._signals(query)
        return [
            self._hit(self._by_id[event_id], lexical_map.get(event_id, 0.0), semantic_map.get(event_id, 0.0))
            for event_id in event_ids
            if event_id in self._by_id
        ]

