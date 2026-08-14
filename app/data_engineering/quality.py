"""Data-quality checks for event streams and snapshot materializations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.data_engineering.models import CDCOperation, EventEnvelope


@dataclass(frozen=True, slots=True)
class DataQualityIssue:
    event_id: str
    code: str
    message: str
    severity: str


@dataclass(slots=True)
class DataQualityReport:
    checked: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    issues: list[DataQualityIssue] = field(default_factory=list)

    @property
    def quality_score(self) -> float:
        if self.checked == 0:
            return 1.0
        return max(0.0, 1.0 - (self.rejected + 0.25 * self.duplicates) / self.checked)


class DataQualityMonitor:
    """Apply schema, snapshot, identity, and duplicate checks."""

    def inspect(self, envelopes: list[EventEnvelope], as_of: datetime) -> tuple[list[EventEnvelope], DataQualityReport]:
        report = DataQualityReport(checked=len(envelopes))
        accepted: list[EventEnvelope] = []
        seen: set[tuple[str, str, str]] = set()
        for envelope in envelopes:
            if not envelope.source.strip() or (
                envelope.operation is not CDCOperation.DELETE and not envelope.content.strip()
            ):
                report.rejected += 1
                report.issues.append(
                    DataQualityIssue(envelope.event_id, "missing_required", "source/content is empty", "error")
                )
                continue
            if envelope.observed_at > as_of:
                report.rejected += 1
                report.issues.append(
                    DataQualityIssue(envelope.event_id, "future_observation", "observed after snapshot", "warning")
                )
                continue
            identity = (envelope.source, envelope.source_event_id, envelope.checksum)
            if identity in seen:
                report.duplicates += 1
                continue
            seen.add(identity)
            accepted.append(envelope)
        report.accepted = len(accepted)
        return accepted, report
