"""Schema validation, CDC envelopes, lineage, and point-in-time ingestion."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data_engineering.models import CDCOperation, EventEnvelope, LineageRecord
from app.data_engineering.quality import DataQualityMonitor, DataQualityReport
from app.memory.models import Event
from app.reasoning.extraction import SignalExtractor
from app.utils.time import parse_timestamp

LOGGER = logging.getLogger(__name__)


class EventLoader:
    """Load raw observations into traceable event-sourced envelopes."""

    processor_version = "event-loader/2.0"

    def __init__(self, extractor: SignalExtractor, as_of: datetime) -> None:
        self.extractor = extractor
        self.as_of = as_of
        self.excluded_future_count = 0
        self.envelopes: list[EventEnvelope] = []
        self.lineage: list[LineageRecord] = []
        self.quality_report = DataQualityReport()

    def load_json(self, path: str | Path) -> list[Event]:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("Dataset root must be a JSON array")
        return self.load_records(payload)

    def _envelope(self, record: dict[str, Any], index: int) -> EventEnvelope:
        try:
            observed = parse_timestamp(str(record.get("observed_at", record["timestamp"])))
            occurred_value = record.get("occurred_at", record.get("timestamp"))
            occurred = parse_timestamp(str(occurred_value)) if occurred_value else None
            source = str(record["source"]).strip().lower()
            content = str(record.get("content", "")).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid event at index {index}: {exc}") from exc
        digest = hashlib.sha1(f"{observed.isoformat()}|{source}|{content}".encode()).hexdigest()[:16]
        source_event_id = str(record.get("id") or record.get("source_event_id") or digest)
        operation = CDCOperation(str(record.get("operation", "upsert")).lower())
        metadata = {
            key: value for key, value in record.items()
            if key not in {"id", "source_event_id", "source", "content", "timestamp", "observed_at", "occurred_at", "operation"}
        }
        return EventEnvelope(
            event_id=digest,
            source_event_id=source_event_id,
            source=source,
            observed_at=observed,
            occurred_at=occurred,
            content=content,
            operation=operation,
            source_cursor=str(record["cursor"]) if record.get("cursor") is not None else None,
            metadata=metadata,
            trace_id=f"trace-{digest}",
        )

    def load_records(self, records: list[dict[str, Any]]) -> list[Event]:
        envelopes = [self._envelope(record, index) for index, record in enumerate(records)]
        accepted, self.quality_report = DataQualityMonitor().inspect(envelopes, self.as_of)
        self.excluded_future_count = sum(
            issue.code == "future_observation" for issue in self.quality_report.issues
        )
        self.envelopes = accepted
        self.lineage = []
        events: list[Event] = []
        processed_at = datetime.now(timezone.utc)
        for envelope in accepted:
            if envelope.operation is CDCOperation.DELETE:
                continue
            event = Event(
                id=envelope.event_id,
                timestamp=envelope.observed_at,
                source=envelope.source,
                content=envelope.content,
                source_event_id=envelope.source_event_id,
                lineage_trace_id=envelope.trace_id,
                metadata=envelope.metadata,
            )
            event.signals = self.extractor.extract(event)
            events.append(event)
            self.lineage.append(
                LineageRecord(
                    trace_id=envelope.trace_id,
                    event_id=event.id,
                    stage="signal_enrichment",
                    input_ids=(envelope.event_id,),
                    output_ids=(event.id,),
                    processor_version=self.processor_version,
                    processed_at=processed_at,
                    metadata={"schema_version": envelope.schema_version},
                )
            )
        events.sort(key=lambda event: (event.timestamp, event.id))
        LOGGER.info(
            "Ingested %d events; excluded %d future observations; quality %.3f",
            len(events),
            self.excluded_future_count,
            self.quality_report.quality_score,
        )
        return events
