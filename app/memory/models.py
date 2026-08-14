"""Typed domain models shared by the memory intelligence system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.utils.time import isoformat


class MemoryStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


@dataclass(slots=True)
class EventSignals:
    is_task: bool = False
    is_commitment: bool = False
    is_follow_up: bool = False
    is_meeting: bool = False
    is_completion: bool = False
    is_cancellation: bool = False
    deadline_at: datetime | None = None
    urgency_score: float = 0.0
    importance_score: float = 0.0
    risk_score: float = 0.0
    source_confidence: float = 0.5
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_task": self.is_task,
            "is_commitment": self.is_commitment,
            "is_follow_up": self.is_follow_up,
            "is_meeting": self.is_meeting,
            "is_completion": self.is_completion,
            "is_cancellation": self.is_cancellation,
            "deadline_at": isoformat(self.deadline_at),
            "urgency_score": round(self.urgency_score, 4),
            "importance_score": round(self.importance_score, 4),
            "risk_score": round(self.risk_score, 4),
            "source_confidence": round(self.source_confidence, 4),
            "reasons": self.reasons,
        }


@dataclass(slots=True)
class Event:
    id: str
    timestamp: datetime
    source: str
    content: str
    signals: EventSignals = field(default_factory=EventSignals)
    source_event_id: str | None = None
    lineage_trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_signals: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "timestamp": isoformat(self.timestamp),
            "source": self.source,
            "content": self.content,
            "source_event_id": self.source_event_id,
            "lineage_trace_id": self.lineage_trace_id,
            "metadata": self.metadata,
        }
        if include_signals:
            result["signals"] = self.signals.to_dict()
        return result


@dataclass(slots=True)
class Commitment:
    id: str
    title: str
    status: MemoryStatus
    first_seen: datetime
    last_seen: datetime
    deadline_at: datetime | None
    evidence_ids: list[str]
    subject_terms: set[str]
    importance_score: float
    urgency_score: float
    risk_score: float
    mention_count: int = 1
    waiting_on: str | None = None
    resolution_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "first_seen": isoformat(self.first_seen),
            "last_seen": isoformat(self.last_seen),
            "deadline_at": isoformat(self.deadline_at),
            "evidence_ids": self.evidence_ids,
            "importance_score": round(self.importance_score, 4),
            "urgency_score": round(self.urgency_score, 4),
            "risk_score": round(self.risk_score, 4),
            "mention_count": self.mention_count,
            "waiting_on": self.waiting_on,
            "resolution_note": self.resolution_note,
        }


@dataclass(slots=True)
class Project:
    id: str
    name: str
    event_ids: list[str]
    centroid: list[float]
    keywords: list[str]
    last_updated: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "event_ids": self.event_ids,
            "keywords": self.keywords,
            "last_updated": isoformat(self.last_updated),
        }


@dataclass(slots=True)
class SemanticFact:
    id: str
    project_id: str
    statement: str
    evidence_ids: list[str]
    valid_at: datetime
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "statement": self.statement,
            "evidence_ids": self.evidence_ids,
            "valid_at": isoformat(self.valid_at),
            "confidence": round(self.confidence, 4),
        }


@dataclass(slots=True)
class RetrievalHit:
    event: Event
    score: float
    semantic_similarity: float
    lexical_score: float
    recency_score: float
    importance_score: float
    source_confidence: float

    def to_dict(self) -> dict[str, Any]:
        result = self.event.to_dict()
        result["retrieval"] = {
            "score": round(self.score, 4),
            "semantic_similarity": round(self.semantic_similarity, 4),
            "lexical_score": round(self.lexical_score, 4),
            "recency_score": round(self.recency_score, 4),
            "importance_score": round(self.importance_score, 4),
            "source_confidence": round(self.source_confidence, 4),
        }
        return result


@dataclass(slots=True)
class QueryAnswer:
    query: str
    answer: str
    selected_context: list[dict[str, Any]]
    reasoning: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "selected_context": self.selected_context,
            "reasoning": self.reasoning,
        }
