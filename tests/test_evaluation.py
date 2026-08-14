"""Evaluation utility tests."""

from app.evaluation.metrics import (
    classification_metrics,
    evidence_coverage,
    expansion_recall_gain,
    hallucination_rate,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    trace_validity_rate,
)


def test_metrics() -> None:
    metrics = classification_metrics({"a", "b"}, {"b", "c"})
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert precision_at_k(["a", "b"], {"b"}, 2) == 0.5
    assert recall_at_k(["a", "b"], {"b", "c"}, 2) == 0.5
    assert ndcg_at_k(["a", "b"], {"b": 2.0}, 2) > 0
    assert expansion_recall_gain(["a"], ["a", "b"], {"b"}) == 1.0
    assert evidence_coverage(["a", "b"], ["b", "c"]) == 0.5
    assert hallucination_rate([("supported", ["event-1"]), ("unsupported", [])]) == 0.5
    assert trace_validity_rate([{"valid": True}, {"valid": False}]) == 0.5
