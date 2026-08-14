"""Embedding-based, label-free project discovery."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from app.memory.models import Event, Project
from app.retrieval.embeddings import Embedder, cosine_similarity
from app.utils.text import jaccard, tokenize, top_terms


@dataclass(slots=True)
class _Cluster:
    event_ids: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)

    @property
    def centroid(self) -> list[float]:
        if not self.vectors:
            return []
        size = len(self.vectors)
        return [sum(values) / size for values in zip(*self.vectors, strict=False)]


class ProjectMemory:
    """Cluster meaningful events by embedding similarity, never by fixed project names."""

    def __init__(self, events: list[Event], embedder: Embedder, threshold: float = 0.42) -> None:
        self.embedder = embedder
        self.threshold = 0.18 if embedder.name == "hashing-fallback" else threshold
        self._events = {event.id: event for event in events}
        self._projects = self._cluster(events)

    def _meaningful(self, event: Event) -> bool:
        signals = event.signals
        return signals.is_task or signals.is_commitment or signals.is_follow_up or signals.importance_score >= 0.42

    @staticmethod
    def _project_name(texts: list[str], keywords: list[str], event_count: int) -> str:
        """Infer a readable label from recurring phrases and discovered entities."""

        acronyms = Counter(
            token.lower()
            for text in texts
            for token in re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", text)
        )
        bigrams = Counter(
            (left, right)
            for text in texts
            for left, right in zip(
                tokenize(text, remove_stopwords=True),
                tokenize(text, remove_stopwords=True)[1:],
                strict=False,
            )
        )
        if acronyms and event_count > 1:
            acronym = acronyms.most_common(1)[0][0]
            entity_phrases = [
                (pair, count) for pair, count in bigrams.items()
                if acronym in pair and count >= 2
            ]
            if entity_phrases:
                pair, _ = max(entity_phrases, key=lambda item: (item[1], item[0]))
                return " ".join(term.upper() if term == acronym else term.title() for term in pair)
        name_terms = keywords[:2] if event_count > 1 else keywords[:3]
        return " ".join(term.upper() if len(term) <= 4 and term.isalpha() else term.title() for term in name_terms)

    def _cluster(self, events: list[Event]) -> list[Project]:
        candidates = [event for event in events if self._meaningful(event)]
        if not candidates:
            return []
        vectors = self.embedder.encode([event.content for event in candidates])
        clusters: list[_Cluster] = []
        for event, vector in zip(candidates, vectors, strict=True):
            best_cluster: _Cluster | None = None
            best_score = -1.0
            for cluster in clusters:
                semantic = max(0.0, cosine_similarity(vector, cluster.centroid))
                lexical = max(jaccard(event.content, text) for text in cluster.texts)
                score = 0.72 * semantic + 0.28 * lexical
                if score > best_score:
                    best_score, best_cluster = score, cluster
            if best_cluster is None or best_score < self.threshold:
                clusters.append(_Cluster([event.id], [event.content], [vector]))
            else:
                best_cluster.event_ids.append(event.id)
                best_cluster.texts.append(event.content)
                best_cluster.vectors.append(vector)

        projects: list[Project] = []
        for cluster in clusters:
            keywords = top_terms(cluster.texts, limit=4)
            if not keywords:
                continue
            name = self._project_name(cluster.texts, keywords, len(cluster.event_ids))
            digest = hashlib.sha1("|".join(sorted(cluster.event_ids)).encode()).hexdigest()[:12]
            projects.append(
                Project(
                    id=f"project-{digest}",
                    name=name,
                    event_ids=cluster.event_ids,
                    centroid=cluster.centroid,
                    keywords=keywords,
                    last_updated=max(self._events[event_id].timestamp for event_id in cluster.event_ids),
                )
            )
        return sorted(projects, key=lambda project: (-len(project.event_ids), project.name))

    def all(self) -> list[Project]:
        return list(self._projects)

    def events(self, project: Project) -> list[Event]:
        return sorted((self._events[event_id] for event_id in project.event_ids), key=lambda event: event.timestamp)

    def closest(self, query: str, limit: int = 3) -> list[Project]:
        if not self._projects:
            return []
        vector = self.embedder.encode([query])[0]
        return sorted(self._projects, key=lambda project: cosine_similarity(vector, project.centroid), reverse=True)[:limit]
