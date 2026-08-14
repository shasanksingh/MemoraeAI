"""Deduplication, contradiction resolution, and bounded context construction."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.memory.commitment import subject_terms
from app.memory.models import RetrievalHit
from app.utils.text import estimate_tokens, jaccard, normalize_text, top_terms


@dataclass(slots=True)
class ContextStats:
    input_count: int = 0
    duplicates_removed: int = 0
    stale_facts_removed: int = 0
    budget_omissions: int = 0
    tokens_used: int = 0
    rolling_summaries: list[dict[str, object]] = field(default_factory=list)


class ContextBuilder:
    """Create compact, current, evidence-preserving query context."""

    CHANGE_MARKERS = (
        "ignore my earlier", "moved from", "moved to", "is now due", "not friday",
        "correction", "do not use the old", "updated", "no longer blocked", "cancel",
    )

    def __init__(self, token_budget: int = 4_000, near_duplicate_threshold: float = 0.88) -> None:
        self.token_budget = token_budget
        self.near_duplicate_threshold = near_duplicate_threshold

    def _deduplicate(self, hits: list[RetrievalHit], stats: ContextStats) -> list[RetrievalHit]:
        kept: list[RetrievalHit] = []
        for hit in sorted(hits, key=lambda value: (value.event.timestamp, value.score), reverse=True):
            duplicate = any(
                normalize_text(hit.event.content) == normalize_text(other.event.content)
                or jaccard(hit.event.content, other.event.content) >= self.near_duplicate_threshold
                for other in kept
            )
            if duplicate:
                stats.duplicates_removed += 1
            else:
                kept.append(hit)
        return kept

    def _resolve_contradictions(self, hits: list[RetrievalHit], stats: ContextStats) -> list[RetrievalHit]:
        newest_first = sorted(hits, key=lambda value: value.event.timestamp, reverse=True)
        changes = [
            hit for hit in newest_first
            if any(marker in hit.event.content.lower() for marker in self.CHANGE_MARKERS)
        ]
        kept: list[RetrievalHit] = []
        for hit in newest_first:
            stale = False
            hit_terms = subject_terms(hit.event.content)
            for change in changes:
                if change.event.timestamp <= hit.event.timestamp:
                    continue
                if change.event.signals.is_meeting != hit.event.signals.is_meeting:
                    continue
                change_terms = subject_terms(change.event.content)
                overlap = len(hit_terms & change_terms)
                containment = overlap / max(1, min(len(hit_terms), len(change_terms)))
                if overlap >= 2 and containment >= 0.35:
                    stale = True
                    break
            if stale:
                stats.stale_facts_removed += 1
            else:
                kept.append(hit)
        return kept

    def prepare(self, hits: list[RetrievalHit]) -> tuple[list[RetrievalHit], ContextStats]:
        stats = ContextStats(input_count=len(hits))
        current = self._resolve_contradictions(self._deduplicate(hits, stats), stats)
        selected: list[RetrievalHit] = []
        omitted: list[RetrievalHit] = []
        tokens = 0
        for hit in sorted(current, key=lambda value: value.score, reverse=True):
            cost = estimate_tokens(hit.event.content) + 18
            if tokens + cost > self.token_budget:
                stats.budget_omissions += 1
                omitted.append(hit)
                continue
            selected.append(hit)
            tokens += cost
        stats.tokens_used = tokens
        for start in range(0, len(omitted), 20):
            window = omitted[start : start + 20]
            chronological = sorted(window, key=lambda value: value.event.timestamp)
            topics = top_terms((hit.event.content for hit in window), limit=5)
            stats.rolling_summaries.append(
                {
                    "type": "rolling_summary",
                    "from": chronological[0].event.timestamp.isoformat(),
                    "to": chronological[-1].event.timestamp.isoformat(),
                    "compressed_event_count": len(window),
                    "topics": topics,
                    "summary": (
                        f"{len(window)} lower-ranked memories compressed; recurring topics: "
                        + (", ".join(topics) if topics else "uncategorized")
                    ),
                }
            )
        return selected, stats
