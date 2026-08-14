"""Temporal parsing, status changes, and point-in-time behavior."""

from __future__ import annotations

from app.ingestion.loader import EventLoader
from app.memory.commitment import CommitmentMemory
from app.memory.models import MemoryStatus, RetrievalHit
from app.reasoning.context import ContextBuilder
from app.reasoning.extraction import SignalExtractor
from app.utils.time import parse_timestamp, resolve_deadline


def _events(records: list[dict[str, str]], as_of: str = "2026-04-07T03:00:00Z"):
    now = parse_timestamp(as_of)
    return EventLoader(SignalExtractor(now), now).load_records(records), now


def test_explicit_correction_uses_non_negated_date() -> None:
    deadline = resolve_deadline(
        "UIE proposal is now due Monday Apr 13 15:00 IST, not Friday Apr 10.",
        parse_timestamp("2026-04-09T07:55:00Z"),
    )
    assert deadline == parse_timestamp("2026-04-13T09:30:00Z")


def test_deadline_change_latest_fact_wins() -> None:
    events, now = _events(
        [
            {"timestamp": "2026-04-01T09:00:00Z", "source": "slack", "content": "Submit Friday"},
            {"timestamp": "2026-04-02T09:00:00Z", "source": "slack", "content": "Submit Monday"},
        ]
    )
    memory = CommitmentMemory(events, now)
    assert len(memory.open()) == 1
    assert memory.open()[0].deadline_at == parse_timestamp("2026-04-06T12:30:00Z")
    assert "supersedes" in (memory.open()[0].resolution_note or "")


def test_completion_closes_prior_task() -> None:
    events, now = _events(
        [
            {"timestamp": "2026-04-01T09:00:00Z", "source": "gmail", "content": "Need to send report"},
            {"timestamp": "2026-04-02T09:00:00Z", "source": "gmail", "content": "Report sent"},
        ]
    )
    memory = CommitmentMemory(events, now)
    assert not memory.open()
    assert memory.all()[0].status is MemoryStatus.COMPLETED


def test_context_suppresses_stale_meeting_date() -> None:
    events, _ = _events(
        [
            {"timestamp": "2026-04-01T09:00:00Z", "source": "calendar", "content": "Planning meeting Friday"},
            {"timestamp": "2026-04-02T09:00:00Z", "source": "calendar", "content": "Planning meeting moved to Monday"},
        ]
    )
    hits = [
        RetrievalHit(event, 0.8, 0.8, 1.0, 0.8, 0.8, 1.0)
        for event in events
    ]
    selected, stats = ContextBuilder().prepare(hits)
    assert len(selected) == 1
    assert "Monday" in selected[0].event.content
    assert stats.stale_facts_removed == 1


def test_future_events_do_not_leak_into_snapshot(system) -> None:
    assert system.future_events_excluded > 0
    assert system.episodic is not None
    assert all(event.timestamp <= system.settings.as_of for event in system.episodic.all())
    rendered = str(system.answer_query("What commitments am I at risk of missing?"))
    assert "Hiring rubric was due Aug 12" not in rendered  # timestamped five minutes after snapshot


def test_task_referencing_standup_is_not_a_meeting() -> None:
    events, _ = _events(
        [{
            "timestamp": "2026-04-01T09:00:00Z",
            "source": "slack",
            "content": "Shashank, can you add owner names to the launch checklist before standup?",
        }]
    )
    assert events[0].signals.is_task
    assert not events[0].signals.is_meeting


def test_moving_meeting_by_minutes_does_not_create_a_deadline() -> None:
    events, _ = _events(
        [{
            "timestamp": "2026-04-12T11:46:00Z",
            "source": "slack",
            "content": "Can we move standup by 30 minutes? Calendar is messy today.",
        }],
        as_of="2026-04-13T03:00:00Z",
    )
    assert events[0].signals.deadline_at is None
