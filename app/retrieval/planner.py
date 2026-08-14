"""Evidence-first retrieval plans built from soft query constraints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.graph.evidence import EvidenceGraph
from app.graph.models import RelationType
from app.utils.text import tokenize
from app.utils.time import isoformat


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    query: str
    query_terms: tuple[str, ...]
    entity_seed_ids: tuple[str, ...]
    requested_relations: tuple[RelationType, ...]
    requested_facets: tuple[str, ...]
    completeness: str
    as_of: datetime
    broad_limit: int
    final_limit: int
    max_rounds: int
    max_hops: int

    def to_dict(self) -> dict[str, object]:
        return {
            "query_terms": list(self.query_terms),
            "entity_seed_ids": list(self.entity_seed_ids),
            "requested_relations": [relation.value for relation in self.requested_relations],
            "requested_facets": list(self.requested_facets),
            "completeness": self.completeness,
            "as_of": isoformat(self.as_of),
            "broad_limit": self.broad_limit,
            "final_limit": self.final_limit,
            "max_rounds": self.max_rounds,
            "max_hops": self.max_hops,
        }


class RetrievalPlanner:
    """Create non-exclusive search constraints; every plan searches broad evidence."""

    _relation_terms = {
        RelationType.BLOCKED_BY: {"blocked", "blocker", "waiting", "dependency", "depends"},
        RelationType.HAS_RISK: {"risk", "risky", "slip", "miss", "overdue"},
        RelationType.HAS_DEADLINE: {"deadline", "due", "when", "today"},
        RelationType.SUPERSEDES: {"changed", "change", "correction", "updated", "history"},
        RelationType.DISCUSSES: {"meeting", "discussed", "call", "review"},
        RelationType.OWNS: {"owner", "owns", "who", "responsible"},
        RelationType.IMPACTS: {"impact", "affect", "why", "because"},
    }

    def __init__(self, broad_limit: int = 80, final_limit: int = 16, max_rounds: int = 3, max_hops: int = 2) -> None:
        self.broad_limit = broad_limit
        self.final_limit = final_limit
        self.max_rounds = max_rounds
        self.max_hops = max_hops

    def plan(self, query: str, graph: EvidenceGraph, as_of: datetime) -> RetrievalPlan:
        terms = tuple(dict.fromkeys(tokenize(query, remove_stopwords=True)))
        term_set = set(terms)
        relations = tuple(relation for relation, markers in self._relation_terms.items() if term_set & markers)
        facets = [relation.value for relation in relations]
        if term_set & {"focus", "priority", "important", "next"}:
            facets.append("priority")
        if term_set & {"all", "everything", "summary", "timeline"}:
            facets.append("coverage")
        if not facets:
            facets.append("relevance")
        completeness = "exhaustive" if term_set & {"all", "everything", "timeline"} else "normal"
        return RetrievalPlan(
            query=query,
            query_terms=terms,
            entity_seed_ids=tuple(node.id for node in graph.find_entities(query)),
            requested_relations=relations,
            requested_facets=tuple(dict.fromkeys(facets)),
            completeness=completeness,
            as_of=as_of,
            broad_limit=self.broad_limit,
            final_limit=self.final_limit,
            max_rounds=self.max_rounds,
            max_hops=self.max_hops,
        )

