"""End-to-end evidence-first query behavior."""

from __future__ import annotations

import pytest


QUERIES = (
    "What should I focus on today?",
    "Which obligation is most likely to slip?",
    "Who are we waiting on?",
    "Summarize everything related to the UIE proposal.",
)


@pytest.mark.parametrize("query", QUERIES)
def test_answer_contract_and_trace(system, query: str) -> None:
    result = system.answer_query(query)
    assert set(result) == {"query", "answer", "selected_context", "reasoning"}
    assert result["query"] == query
    assert result["answer"]
    assert result["selected_context"]
    assert {
        "retrieval_trace", "context_quality", "context_stats", "claim_validation", "snapshot", "supported_claims"
    } <= set(result["reasoning"])
    trace = result["reasoning"]["retrieval_trace"]
    assert trace["rounds"][0]["operation"] == "parallel sparse/vector broad recall"
    assert trace["selected_memory_layers"]
    assert result["reasoning"]["claim_validation"]["valid"]
    assert "[evidence:" not in result["answer"]


def test_unknown_risk_paraphrase_discovers_risk_evidence(system) -> None:
    result = system.answer_query("Which obligation is most likely to slip?")
    assert "Risks and blockers:" in result["answer"]
    assert "air conditioning" not in result["answer"]
    assert "has_risk" in result["reasoning"]["retrieval_trace"]["plan"]["requested_relations"]


def test_change_query_constructs_corrected_value(system) -> None:
    result = system.answer_query("What changed about the licensing estimate?")
    assert "$48.5k" in result["answer"]
    assert any("$42k" in item["content"] and "$48.5k" in item["content"] for item in result["selected_context"])


def test_summary_recovers_commercial_evidence_through_expansion(system) -> None:
    result = system.answer_query("Summarize everything related to the UIE proposal.")
    contents = " ".join(str(item["content"]) for item in result["selected_context"])
    assert "Thursday Aug 13 15:00 IST" in contents
    assert "$48.5k" in contents
    assert "Unified Intelligence Engine" in contents
