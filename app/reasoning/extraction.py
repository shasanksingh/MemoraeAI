"""Explainable, label-free signal extraction from personal events."""

from __future__ import annotations

import re
from datetime import datetime

from app.memory.models import Event, EventSignals
from app.utils.time import resolve_deadline

SOURCE_CONFIDENCE = {
    "calendar": 1.00,
    "reminder": 0.95,
    "gmail": 0.88,
    "email": 0.88,
    "notion": 0.78,
    "slack": 0.74,
    "whatsapp": 0.66,
    "sms": 0.58,
    "chrome_extension": 0.35,
}

COMMITMENT_PATTERNS = (
    r"\bi(?:'ll| will| promised| owe)\b",
    r"\blet me handle\b",
    r"\bwe promised\b",
    r"\byou said you would\b",
)
TASK_PATTERNS = (
    r"\bneed(?:s)? to\b", r"\bplease\b", r"\bcan you\b", r"\bremind me\b",
    r"\bfollow up\b", r"\bnudge\b", r"\bconfirm\b", r"\bcollect\b", r"\badd\b",
    r"\bbring\b", r"\bupload\b", r"\bpay\b", r"\breview and close\b", r"\bdue\b",
)
FOLLOW_UP_PATTERNS = (r"\bremind\b", r"\bfollow up\b", r"\bcheck back\b", r"\bwaiting on\b", r"\bnudge\b", r"\bcircle back\b")
RISK_PATTERNS = (r"still (?:haven't|hasn't|need)", r"\bhaven't\b", r"\bdelayed\b", r"\bpushed back\b", r"\bslips? again\b", r"\bbefore i forget again\b", r"\boverdue\b", r"\bstill blank\b")
COMPLETION_PATTERNS = (r"\b(?:sent|submitted|finished|completed|done|resolved|approved)\b", r"\bno longer blocked\b", r"\bnow has\b")
CANCELLATION_PATTERNS = (r"\bcancel(?:led|ation)?\b", r"\bremoved\b", r"\bdon't (?:send|book|do)\b")
SCHEDULED_MEETING_PATTERNS = (
    r"\blet'?s meet\b",
    r"\b(?:meeting|call|sync|standup|appointment|session|critique)\b.{0,32}"
    r"\b(?:scheduled|moved|today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"apr(?:il)?|\d{1,2}:\d{2})\b",
)
NOISE_PATTERNS = (
    r"\bnewsletter\b", r"\breceipt(?: is ready| attached| from)\b", r"\botp is\b",
    r"\bsaved link\b", r"\bpromo\b", r"\bworkspace digest\b", r"\bcoffee machine\b",
    r"\blunch is late\b", r"\bair conditioning\b", r"\bpackage delivered\b", r"\bfocus playlist\b",
)
PREFERENCE_PATTERNS = (
    r"\bi (?:prefer|like|hate)\b", r"\bdefault me to\b", r"\bkeep .* clear\b",
    r"\bplease (?:keep|avoid)\b", r"\bno cilantro\b", r"\bfamily time unless\b",
)
DEADLINE_CONTEXT_PATTERNS = (
    r"\bdue\b",
    r"\bby\s+(?:eod|end of day|tomorrow|today|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|apr(?:il)?)\b",
    r"\bbefore\b", r"\bsend\b", r"\bsubmit\b", r"\bmeeting\b",
    r"\breview\b", r"\bappointment\b", r"\bscheduled\b", r"\bmoved\b", r"\bcall\b",
    r"\bsync\b", r"\bblock\b", r"\bvisit\b", r"\brenew\b", r"\bconfirm\b", r"\bupload\b",
    r"\bpay\b", r"\bdeliver\b",
)


class SignalExtractor:
    """Infer action, deadline, urgency, importance, and risk without labels."""

    def __init__(self, as_of: datetime) -> None:
        self.as_of = as_of

    @staticmethod
    def _matches(patterns: tuple[str, ...], text: str) -> bool:
        return any(re.search(pattern, text, re.I) for pattern in patterns)

    def extract(self, event: Event) -> EventSignals:
        text = event.content
        lowered = text.lower()
        confidence = SOURCE_CONFIDENCE.get(event.source, 0.5)
        is_noise = self._matches(NOISE_PATTERNS, lowered)
        is_preference = self._matches(PREFERENCE_PATTERNS, lowered)
        has_deadline_context = event.source == "calendar" or self._matches(DEADLINE_CONTEXT_PATTERNS, lowered)
        deadline = None if is_noise or is_preference or not has_deadline_context else resolve_deadline(text, event.timestamp)
        is_commitment = not is_noise and self._matches(COMMITMENT_PATTERNS, lowered)
        is_follow_up = not is_noise and self._matches(FOLLOW_UP_PATTERNS, lowered)
        # A task can reference a meeting ("send before standup") without being
        # the meeting itself. Only explicit scheduling language or a calendar
        # source creates a meeting memory.
        is_meeting = not is_noise and (
            event.source == "calendar" or self._matches(SCHEDULED_MEETING_PATTERNS, lowered)
        )
        is_task = not is_noise and not is_preference and (
            is_commitment
            or is_follow_up
            or self._matches(TASK_PATTERNS, lowered)
            or (deadline is not None and not lowered.startswith("focus block"))
        )
        has_remaining_action = bool(re.search(r"\b(?:still|only)?\s*needs?\b|\bstill\b.*\b(?:need|missing|blank)\b", lowered))
        is_completion = not is_noise and not has_remaining_action and self._matches(COMPLETION_PATTERNS, lowered)
        is_cancellation = not is_noise and self._matches(CANCELLATION_PATTERNS, lowered)

        importance = 0.10 + 0.25 * confidence
        reasons: list[str] = []
        if is_commitment:
            importance += 0.22
            reasons.append("explicit promise/obligation language")
        if is_task:
            importance += 0.12
            reasons.append("action-request language")
        if deadline:
            importance += 0.18
            reasons.append("explicit or relative deadline")
        if re.search(r"\b(customer|proposal|production|legal|finance|school|mom|parent|insurance|risk|launch|incident)\b", lowered):
            importance += 0.14
            reasons.append("high-impact domain")
        if is_noise:
            importance = min(importance, 0.12)
            reasons.append("low-action informational pattern")

        urgency = 0.05 if is_task or is_meeting else 0.0
        if deadline:
            hours = (deadline - self.as_of).total_seconds() / 3_600
            if hours <= 0:
                urgency = 1.0
                reasons.append("deadline is overdue")
            elif hours <= 12:
                urgency = 0.92
                reasons.append("deadline within 12 hours")
            elif hours <= 48:
                urgency = 0.75
                reasons.append("deadline within 48 hours")
            elif hours <= 7 * 24:
                urgency = 0.48
            else:
                urgency = 0.22
        explicit_risk = self._matches(RISK_PATTERNS, lowered)
        risk = 0.05 if is_task else 0.0
        if explicit_risk:
            risk += 0.45
            reasons.append("explicit delay/procrastination language")
        if deadline:
            hours = (deadline - self.as_of).total_seconds() / 3_600
            if hours < 0 and not is_completion:
                risk += 0.42
            elif hours <= 24 and not is_completion:
                risk += 0.28
        if is_completion or is_cancellation:
            risk = 0.0

        return EventSignals(
            is_task=is_task,
            is_commitment=is_commitment,
            is_follow_up=is_follow_up,
            is_meeting=is_meeting,
            is_completion=is_completion,
            is_cancellation=is_cancellation,
            deadline_at=deadline,
            urgency_score=min(1.0, urgency),
            importance_score=min(1.0, importance),
            risk_score=min(1.0, risk),
            source_confidence=confidence,
            reasons=reasons,
        )
