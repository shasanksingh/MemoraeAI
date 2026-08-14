"""Dependency-free Okapi BM25 candidate retrieval."""

from __future__ import annotations

import math
from collections import Counter

from app.memory.models import Event
from app.utils.text import tokenize


class BM25Index:
    """Small BM25 implementation used for high-recall Stage 1 retrieval."""

    def __init__(self, events: list[Event], k1: float = 1.5, b: float = 0.75) -> None:
        self.events = events
        self.k1 = k1
        self.b = b
        self.documents = [tokenize(event.content) for event in events]
        self.term_frequencies = [Counter(document) for document in self.documents]
        self.avg_length = sum(map(len, self.documents)) / max(1, len(self.documents))
        self.document_frequency = Counter(
            token for document in self.documents for token in set(document)
        )

    def _idf(self, term: str) -> float:
        count = self.document_frequency.get(term, 0)
        total = len(self.documents)
        return math.log(1.0 + (total - count + 0.5) / (count + 0.5))

    def search(self, query: str, limit: int = 40) -> list[tuple[str, float]]:
        query_terms = tokenize(query)
        scores: list[tuple[str, float]] = []
        for event, document, frequencies in zip(self.events, self.documents, self.term_frequencies, strict=True):
            score = 0.0
            length_normalizer = self.k1 * (1 - self.b + self.b * len(document) / max(1.0, self.avg_length))
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                score += self._idf(term) * (frequency * (self.k1 + 1)) / (frequency + length_normalizer)
            if score > 0:
                scores.append((event.id, score))
        return sorted(scores, key=lambda item: (-item[1], item[0]))[:limit]
