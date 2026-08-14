"""Incremental event processing with checkpoints and lineage output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.data_engineering.models import EventEnvelope, LineageRecord
from app.data_engineering.quality import DataQualityMonitor, DataQualityReport


class MaterializedView(Protocol):
    name: str

    def apply(self, envelope: EventEnvelope) -> tuple[str, ...]: ...


@dataclass(slots=True)
class ProcessingResult:
    accepted_event_ids: list[str]
    lineage: list[LineageRecord]
    quality: DataQualityReport
    checkpoints: dict[str, str]
    view_outputs: dict[str, list[str]] = field(default_factory=dict)


class IncrementalEventProcessor:
    """Process only new CDC observations and update registered views."""

    version = "incremental-processor/1.0"

    def __init__(self, quality_monitor: DataQualityMonitor | None = None) -> None:
        self.quality_monitor = quality_monitor or DataQualityMonitor()
        self._checksums: set[str] = set()
        self._checkpoints: dict[str, str] = {}

    def process(
        self,
        envelopes: list[EventEnvelope],
        *,
        as_of: datetime,
        views: tuple[MaterializedView, ...] = (),
    ) -> ProcessingResult:
        quality_input, report = self.quality_monitor.inspect(envelopes, as_of)
        unseen = [item for item in quality_input if item.checksum not in self._checksums]
        report.duplicates += len(quality_input) - len(unseen)
        report.accepted = len(unseen)
        lineage: list[LineageRecord] = []
        outputs: dict[str, list[str]] = {view.name: [] for view in views}
        now = datetime.now(timezone.utc)
        for envelope in unseen:
            self._checksums.add(envelope.checksum)
            if envelope.source_cursor:
                self._checkpoints[envelope.source] = envelope.source_cursor
            for view in views:
                output_ids = view.apply(envelope)
                outputs[view.name].extend(output_ids)
                lineage.append(
                    LineageRecord(
                        trace_id=envelope.trace_id,
                        event_id=envelope.event_id,
                        stage=f"materialize:{view.name}",
                        input_ids=(envelope.event_id,),
                        output_ids=output_ids,
                        processor_version=self.version,
                        processed_at=now,
                    )
                )
        return ProcessingResult(
            accepted_event_ids=[item.event_id for item in unseen],
            lineage=lineage,
            quality=report,
            checkpoints=dict(self._checkpoints),
            view_outputs=outputs,
        )

