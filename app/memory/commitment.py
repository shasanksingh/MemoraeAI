"""Commitment memory with temporal status and contradiction resolution."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from app.memory.models import Commitment, Event, MemoryStatus
from app.utils.text import concise_title, tokenize
from app.utils.time import human_delta, isoformat

SUBJECT_EXCLUSIONS = {
    "add", "approved", "before", "bring", "cancelled", "close", "confirm", "done", "due",
    "eod", "finish", "follow", "friday", "handle", "monday", "morning", "moved", "nudge",
    "calendar", "invite", "location", "minutes", "move", "please", "promised", "review",
    "saturday", "scheduled", "sent", "sunday",
    "thursday", "today", "tomorrow", "tonight", "tuesday", "update", "wednesday", "week",
}


def subject_terms(text: str) -> set[str]:
    """Return action-subject terms while removing dates and workflow verbs."""

    terms = set(tokenize(concise_title(text), remove_stopwords=True)) - SUBJECT_EXCLUSIONS
    normalized = {term[:-1] if len(term) > 4 and term.endswith("s") else term for term in terms}
    return {term for term in normalized if not re.fullmatch(r"20\d{2}|\d{1,2}(?:\d{2})?", term)}


class CommitmentMemory:
    """Consolidate obligation mentions into open or terminal commitments."""

    def __init__(self, events: list[Event], as_of: datetime) -> None:
        self.as_of = as_of
        self._events = {event.id: event for event in events}
        self._commitments = self._build(events)

    @staticmethod
    def _same_subject(left: set[str], right: set[str]) -> bool:
        if not left or not right:
            return False
        common = left & right
        if not common:
            return False
        containment = len(common) / min(len(left), len(right))
        union = len(left | right)
        return (
            containment >= 0.50
            or len(common) >= 2 and len(common) / union >= 0.20
            or len(common) >= 2 and any(len(term) >= 5 for term in common)
        )

    def _matching(self, terms: set[str], commitments: list[Commitment], event: Event) -> Commitment | None:
        candidates: list[Commitment] = []
        for item in commitments:
            first_evidence = self._events[item.evidence_ids[0]]
            if first_evidence.signals.is_meeting != event.signals.is_meeting:
                continue
            if self._same_subject(terms, item.subject_terms):
                candidates.append(item)
        if not candidates:
            return None
        return max(candidates, key=lambda item: (len(terms & item.subject_terms), item.last_seen))

    @staticmethod
    def _waiting_on(content: str) -> str | None:
        match = re.search(r"\bwaiting on\s+([^,.;]+)", content, re.I)
        if match:
            return match.group(1).strip()
        match = re.search(r"\bstill need\s+([^,.;]+)", content, re.I)
        return match.group(1).strip() if match else None

    def _build(self, events: list[Event]) -> list[Commitment]:
        commitments: list[Commitment] = []
        for event in events:
            signals = event.signals
            actionable = signals.is_task or signals.is_commitment or signals.is_meeting
            if not actionable and not signals.is_completion and not signals.is_cancellation:
                continue
            terms = subject_terms(event.content)
            current = self._matching(terms, commitments, event)
            if current is None:
                if not actionable or signals.is_completion or signals.is_cancellation:
                    continue
                digest = hashlib.sha1(" ".join(sorted(terms)).encode()).hexdigest()[:12]
                current = Commitment(
                    id=f"commitment-{digest}",
                    title=concise_title(event.content),
                    status=MemoryStatus.OPEN,
                    first_seen=event.timestamp,
                    last_seen=event.timestamp,
                    deadline_at=signals.deadline_at,
                    evidence_ids=[event.id],
                    subject_terms=terms,
                    importance_score=signals.importance_score,
                    urgency_score=signals.urgency_score,
                    risk_score=signals.risk_score,
                    waiting_on=self._waiting_on(event.content),
                )
                commitments.append(current)
                continue

            previous_deadline = current.deadline_at
            current.last_seen = event.timestamp
            current.evidence_ids.append(event.id)
            current.mention_count += 1
            current.importance_score = max(current.importance_score, signals.importance_score)
            current.urgency_score = max(current.urgency_score, signals.urgency_score)
            current.risk_score = max(current.risk_score, signals.risk_score)
            waiting_on = self._waiting_on(event.content)
            if waiting_on:
                current.waiting_on = waiting_on

            if signals.deadline_at is not None:
                current.deadline_at = signals.deadline_at
                if previous_deadline and previous_deadline != current.deadline_at:
                    current.resolution_note = (
                        f"Latest deadline {isoformat(current.deadline_at)} supersedes "
                        f"{isoformat(previous_deadline)}."
                    )
                    current.title = concise_title(event.content)
                    # A corrected future deadline must not retain risk computed
                    # from the now-stale earlier deadline.
                    current.urgency_score = signals.urgency_score
                    current.risk_score = signals.risk_score

            lowered = event.content.lower()
            if signals.is_cancellation:
                current.status = MemoryStatus.CANCELLED
                current.resolution_note = "Latest related event cancelled or removed this item."
            elif "no longer blocked" in lowered or re.search(r"\bblock(?:er|ed)\b.*\b(?:resolved|approved)\b", lowered):
                current.status = MemoryStatus.OPEN
                current.waiting_on = None
                current.risk_score = max(0.1, current.risk_score - 0.25)
                current.resolution_note = "The latest event resolves the blocker; remaining action stays open."
            elif signals.is_completion:
                current.status = MemoryStatus.COMPLETED
                current.risk_score = 0.0
                current.urgency_score = 0.0
                current.resolution_note = "Latest related event provides completion evidence."
            elif actionable and current.status in {MemoryStatus.COMPLETED, MemoryStatus.CANCELLED}:
                current.status = MemoryStatus.OPEN
                current.resolution_note = "A newer action request reopened the item."

        for item in commitments:
            if item.status is not MemoryStatus.OPEN:
                continue
            latest = self._events[item.evidence_ids[-1]]
            pure_calendar_occurrence = (
                latest.source == "calendar"
                and item.deadline_at is not None
                and item.deadline_at < self.as_of
                and re.search(
                    r"\b(meeting|review|appointment|call|standup|visit|session|focus block|working block|sync)\b",
                    latest.content,
                    re.I,
                )
            )
            if pure_calendar_occurrence:
                item.status = MemoryStatus.COMPLETED
                item.risk_score = 0.0
                item.urgency_score = 0.0
                item.resolution_note = "Past calendar occurrence expired from the open-work queue."
                continue
            repetition = min(0.24, 0.06 * max(0, item.mention_count - 1))
            item.risk_score = min(1.0, item.risk_score + repetition)
            if item.deadline_at:
                hours = (item.deadline_at - self.as_of).total_seconds() / 3_600
                if hours < 0:
                    item.risk_score = max(item.risk_score, 0.82)
                    item.urgency_score = 1.0
                elif hours <= 24:
                    item.risk_score = max(item.risk_score, 0.62)
                    item.urgency_score = max(item.urgency_score, 0.9)
        return commitments

    def all(self) -> list[Commitment]:
        return list(self._commitments)

    def open(self) -> list[Commitment]:
        return [item for item in self._commitments if item.status is MemoryStatus.OPEN]

    def at_risk(self, minimum: float = 0.45) -> list[Commitment]:
        return sorted(
            (item for item in self.open() if item.risk_score >= minimum),
            key=lambda item: (-item.risk_score, -item.importance_score, item.deadline_at or datetime.max.replace(tzinfo=self.as_of.tzinfo)),
        )

    def procrastinated(self) -> list[Commitment]:
        candidates: list[Commitment] = []
        for item in self.open():
            evidence = self.evidence(item)
            pure_meeting = bool(evidence) and all(event.signals.is_meeting for event in evidence)
            has_delay_evidence = any(
                "delay/procrastination" in reason
                for event in evidence
                for reason in event.signals.reasons
            )
            if pure_meeting and not has_delay_evidence:
                continue
            if item.mention_count >= 2 or item.risk_score >= 0.65 or item.waiting_on:
                candidates.append(item)
        return sorted(candidates, key=lambda item: (-item.mention_count, -item.risk_score, -item.importance_score))

    def evidence(self, item: Commitment) -> list[Event]:
        return [self._events[event_id] for event_id in item.evidence_ids if event_id in self._events]

    def rationale(self, item: Commitment) -> str:
        pieces = [f"{item.mention_count} mention(s)", human_delta(item.deadline_at, self.as_of)]
        if item.waiting_on:
            pieces.append(f"waiting on {item.waiting_on}")
        if item.resolution_note:
            pieces.append(item.resolution_note)
        return "; ".join(pieces)
