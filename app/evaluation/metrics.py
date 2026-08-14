"""Metrics for graph, retrieval, context, evidence, and answer quality."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class GraphQualityMetrics:
    entity_precision: float
    entity_recall: float
    relationship_precision: float
    relationship_recall: float
    provenance_coverage: float


@dataclass(frozen=True, slots=True)
class ContextMetrics:
    evidence_coverage: float
    evidence_density: float
    redundancy_rate: float
    stale_as_current_rate: float
    facet_coverage: float


def classification_metrics(predicted: Iterable[str], expected: Iterable[str]) -> ClassificationMetrics:
    predicted_set, expected_set = set(predicted), set(expected)
    true_positive = len(predicted_set & expected_set)
    precision = true_positive / max(1, len(predicted_set))
    recall = true_positive / max(1, len(expected_set))
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return ClassificationMetrics(precision, recall, f1)


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    top = ranked_ids[:k]
    return sum(event_id in relevant_ids for event_id in top) / k


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    return len(set(ranked_ids[:k]) & relevant_ids) / max(1, len(relevant_ids))


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    return next((1.0 / rank for rank, item in enumerate(ranked_ids, 1) if item in relevant_ids), 0.0)


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    dcg = sum(
        (2 ** relevance.get(item, 0.0) - 1) / math.log2(rank + 1)
        for rank, item in enumerate(ranked_ids[:k], 1)
    )
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2 ** gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    return dcg / max(1e-12, idcg)


def expansion_recall_gain(
    broad_ids: list[str],
    expanded_ids: list[str],
    relevant_ids: set[str],
) -> float:
    broad = len(set(broad_ids) & relevant_ids) / max(1, len(relevant_ids))
    expanded = len(set(expanded_ids) & relevant_ids) / max(1, len(relevant_ids))
    return expanded - broad


def expansion_precision(broad_ids: list[str], expanded_ids: list[str], relevant_ids: set[str]) -> float:
    additions = set(expanded_ids) - set(broad_ids)
    return len(additions & relevant_ids) / max(1, len(additions))


def evidence_coverage(selected_ids: Iterable[str], gold_evidence_ids: Iterable[str]) -> float:
    selected, gold = set(selected_ids), set(gold_evidence_ids)
    return len(selected & gold) / max(1, len(gold))


def facet_coverage(covered_facets: Iterable[str], required_facets: Iterable[str]) -> float:
    covered, required = set(covered_facets), set(required_facets)
    return len(covered & required) / max(1, len(required))


def graph_quality_metrics(
    predicted_entities: Iterable[str],
    gold_entities: Iterable[str],
    predicted_relationships: Iterable[str],
    gold_relationships: Iterable[str],
    evidence_linked_items: int,
    derived_items: int,
) -> GraphQualityMetrics:
    entities = classification_metrics(predicted_entities, gold_entities)
    relationships = classification_metrics(predicted_relationships, gold_relationships)
    return GraphQualityMetrics(
        entities.precision,
        entities.recall,
        relationships.precision,
        relationships.recall,
        evidence_linked_items / max(1, derived_items),
    )


def context_quality_metrics(
    selected_evidence: Iterable[str],
    gold_evidence: Iterable[str],
    supporting_tokens: int,
    total_tokens: int,
    duplicate_items: int,
    total_items: int,
    stale_current_items: int,
    covered_facets: Iterable[str],
    required_facets: Iterable[str],
) -> ContextMetrics:
    return ContextMetrics(
        evidence_coverage(selected_evidence, gold_evidence),
        supporting_tokens / max(1, total_tokens),
        duplicate_items / max(1, total_items),
        stale_current_items / max(1, total_items),
        facet_coverage(covered_facets, required_facets),
    )


def hallucination_rate(claim_evidence: Iterable[tuple[str, list[str]]]) -> float:
    claims = list(claim_evidence)
    if not claims:
        return 0.0
    return sum(not evidence for _, evidence in claims) / len(claims)


def trace_validity_rate(validations: Iterable[dict[str, object]]) -> float:
    results = list(validations)
    return sum(bool(item.get("valid")) for item in results) / max(1, len(results))

