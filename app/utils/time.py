"""Timezone-safe parsing and relative deadline resolution."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def isoformat(value: datetime | None) -> str | None:
    """Serialize a datetime consistently using a trailing ``Z``."""

    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _clock(text: str, default_hour: int = 18) -> tuple[int, int]:
    time_matches = list(re.finditer(r"\b([01]?\d|2[0-3])(?::([0-5]\d))\s*(?:IST)?\b", text, re.I))
    if time_matches:
        match = time_matches[-1]
        return int(match.group(1)), int(match.group(2) or 0)
    lowered = text.lower()
    if "morning" in lowered:
        return 10, 0
    if "noon" in lowered:
        return 12, 0
    if "tonight" in lowered:
        return 21, 0
    if "eod" in lowered or "end of day" in lowered:
        return 18, 0
    return default_hour, 0


def resolve_deadline(text: str, event_time: datetime) -> datetime | None:
    """Resolve common natural-language deadlines relative to an event timestamp.

    Explicit month/day values take precedence. When text contains a change such as
    ``moved from Apr 10 ... to Apr 13 ...``, the last explicit date is returned.
    Date-only deadlines default to 18:00 IST.
    """

    local_event = event_time.astimezone(IST)
    explicit = list(
        re.finditer(
            r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:,?\s+(20\d{2}))?"
            r"(?:\s+(?:at\s+)?([01]?\d|2[0-3])(?::([0-5]\d)))?\s*(IST)?\b",
            text,
            re.I,
        )
    )
    if explicit:
        lowered = text.lower()
        # Changes normally use the last date (``from X to Y``), except the
        # common correction shape ``now due X, not Y`` where Y is negated.
        if "now due" in lowered and ", not" in lowered:
            due_offset = lowered.index("now due")
            match = next((candidate for candidate in explicit if candidate.start() > due_offset), explicit[0])
        else:
            match = explicit[-1]
        # A later relative action can be distinct from the explicit calendar
        # occurrence: ``appointment Apr 14; send the report tonight``.
        relative_matches = list(re.finditer(r"\b(tomorrow|today|tonight|eod|end of day)\b", lowered))
        if relative_matches and relative_matches[-1].start() > match.end():
            relative = relative_matches[-1].group(1)
            hour, minute = _clock(lowered[relative_matches[-1].start():])
            day_delta = 1 if relative == "tomorrow" else 0
            target = local_event.date() + timedelta(days=day_delta)
            return datetime(target.year, target.month, target.day, hour, minute, tzinfo=IST).astimezone(UTC)

        month = MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        year = int(match.group(3) or local_event.year)
        hour = int(match.group(4)) if match.group(4) is not None else _clock(text)[0]
        minute = int(match.group(5) or 0)
        try:
            return datetime(year, month, day, hour, minute, tzinfo=IST).astimezone(UTC)
        except ValueError:
            return None

    lowered = text.lower()
    hour, minute = _clock(text)
    if re.search(r"\btomorrow\b", lowered):
        target = local_event.date() + timedelta(days=1)
        return datetime(target.year, target.month, target.day, hour, minute, tzinfo=IST).astimezone(UTC)
    if re.search(r"\b(today|tonight|eod|end of day)\b", lowered):
        target = local_event.date()
        return datetime(target.year, target.month, target.day, hour, minute, tzinfo=IST).astimezone(UTC)

    weekday_matches = list(re.finditer(r"\b(" + "|".join(WEEKDAYS) + r")\b", lowered))
    if weekday_matches:
        weekday = WEEKDAYS[weekday_matches[-1].group(1)]
        delta = (weekday - local_event.weekday()) % 7
        candidate = local_event.date() + timedelta(days=delta)
        local_deadline = datetime(candidate.year, candidate.month, candidate.day, hour, minute, tzinfo=IST)
        if local_deadline <= local_event:
            local_deadline += timedelta(days=7)
        return local_deadline.astimezone(UTC)
    return None


def recency_score(timestamp: datetime, as_of: datetime, half_life_days: float = 7.0) -> float:
    """Return an exponential recency score in [0, 1]."""

    age_days = max(0.0, (as_of - timestamp).total_seconds() / 86_400)
    return 0.5 ** (age_days / half_life_days)


def human_delta(deadline: datetime | None, as_of: datetime) -> str:
    """Describe time remaining relative to the snapshot."""

    if deadline is None:
        return "no explicit deadline"
    hours = (deadline - as_of).total_seconds() / 3_600
    if hours < 0:
        return f"overdue by {abs(hours):.1f}h"
    if hours < 24:
        return f"due in {hours:.1f}h"
    return f"due in {hours / 24:.1f}d"
