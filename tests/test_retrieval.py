"""Broad recall, GraphRAG expansion, and bounded-context tests."""

from __future__ import annotations

from app.reasoning.context import ContextBuilder
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.hybrid import HybridRetriever


def test_recall_score_prioritizes_query_relevance(system) -> None:
    assert system.episodic is not None
    retriever = HybridRetriever(system.episodic.all(), HashingEmbedder(), system.settings.as_of)
    hit = retriever.retrieve("UIE licensing estimate", limit=1)[0]
    assert "UIE" in hit.event.content
    assert hit.lexical_score > 0 or hit.semantic_similarity > 0


def test_every_query_uses_broad_recall_then_expansion(system) -> None:
    result = system.answer_query("Who is blocked and what depends on it?")
    rounds = result["reasoning"]["retrieval_trace"]["rounds"]
    assert rounds[0]["operation"] == "parallel sparse/vector broad recall"
    assert any("expansion" in item["operation"] for item in rounds[1:])


def test_context_builder_respects_budget(system) -> None:
    assert system.episodic is not None
    retriever = HybridRetriever(system.episodic.all(), HashingEmbedder(), system.settings.as_of)
    hits = retriever.retrieve("UIE proposal", limit=30)
    selected, stats = ContextBuilder(token_budget=80).prepare(hits)
    assert selected
    assert stats.tokens_used <= 80
    assert stats.budget_omissions > 0

