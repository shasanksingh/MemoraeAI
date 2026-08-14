"""Coverage for extraction and all four memory layers."""

from __future__ import annotations


def test_every_episode_has_bounded_scores(system) -> None:
    assert system.episodic is not None
    for event in system.episodic.all():
        signals = event.signals
        assert 0.0 <= signals.urgency_score <= 1.0
        assert 0.0 <= signals.importance_score <= 1.0
        assert 0.0 <= signals.risk_score <= 1.0
        assert 0.0 <= signals.source_confidence <= 1.0


def test_project_names_are_inferred_from_cluster_terms(system) -> None:
    assert system.projects is not None
    related = [
        project for project in system.projects.all()
        if {"uie", "proposal"} & set(project.keywords)
    ]
    assert related
    assert all(project.name and project.event_ids and project.centroid for project in related)


def test_semantic_facts_are_evidence_linked(system) -> None:
    assert system.semantic is not None
    facts = system.semantic.all()
    assert facts
    assert all(fact.evidence_ids and 0.0 <= fact.confidence <= 1.0 for fact in facts)


def test_source_confidence_ordering(system) -> None:
    assert system.episodic is not None
    confidence = {}
    for event in system.episodic.all():
        confidence.setdefault(event.source, event.signals.source_confidence)
    assert confidence["calendar"] > confidence["gmail"] > confidence["slack"] > confidence["whatsapp"]


def test_sqlite_snapshot_persists_every_layer(system, tmp_path) -> None:
    counts = system.persist(tmp_path / "snapshot.sqlite3")
    assert counts["episodes"] == system.snapshot()["counts"]["episodes"]
    assert counts["commitments"] == system.snapshot()["counts"]["commitments"]
    assert counts["projects"] > 0
    assert counts["semantic_facts"] > 0
