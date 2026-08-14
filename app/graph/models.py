"""Typed nodes and edges for the personal knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    EVENT = "event"
    PERSON = "person"
    PROJECT = "project"
    TASK = "task"
    MEETING = "meeting"
    DECISION = "decision"
    DEADLINE = "deadline"
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    RISK = "risk"
    DEPENDENCY = "dependency"
    PREFERENCE = "preference"
    ACTIVITY = "activity"
    GOAL = "goal"
    LEARNING = "learning"
    TOPIC = "topic"


class RelationType(str, Enum):
    MENTIONS = "mentions"
    EVIDENCE_FOR = "evidence_for"
    OWNS = "owns"
    BELONGS_TO = "belongs_to"
    DEPENDS_ON = "depends_on"
    BLOCKED_BY = "blocked_by"
    UNBLOCKS = "unblocks"
    DISCUSSES = "discusses"
    CONTAINS = "contains"
    IMPACTS = "impacts"
    HAS_DEADLINE = "has_deadline"
    HAS_RISK = "has_risk"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    COMPLETES = "completes"
    TEMPORALLY_ADJACENT = "temporally_adjacent"
    RELATED_TO = "related_to"
    ALIAS_OF = "alias_of"
    COLLABORATES_WITH = "collaborates_with"


@dataclass(frozen=True, slots=True)
class EntityMention:
    entity_id: str
    canonical_name: str
    node_type: NodeType
    text: str
    start: int
    end: int
    confidence: float


@dataclass(slots=True)
class GraphNode:
    id: str
    node_type: NodeType
    label: str
    evidence_ids: set[str] = field(default_factory=set)
    aliases: set[str] = field(default_factory=set)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "label": self.label,
            "evidence_ids": sorted(self.evidence_ids),
            "aliases": sorted(self.aliases),
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source_id: str
    target_id: str
    relation: RelationType
    evidence_ids: tuple[str, ...]
    confidence: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.source_id}|{self.relation.value}|{self.target_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "evidence_ids": list(self.evidence_ids),
            "confidence": round(self.confidence, 4),
            "attributes": self.attributes,
        }
