"""Versioned event and lineage models used by the processing pipeline."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.utils.time import isoformat


class CDCOperation(str, Enum):
    UPSERT = "upsert"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Append-only source observation with CDC and schema metadata."""

    event_id: str
    source_event_id: str
    source: str
    observed_at: datetime
    occurred_at: datetime | None
    content: str
    operation: CDCOperation = CDCOperation.UPSERT
    schema_version: str = "1.0"
    source_cursor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def checksum(self) -> str:
        canonical = json.dumps(
            {
                "source_event_id": self.source_event_id,
                "source": self.source,
                "observed_at": isoformat(self.observed_at),
                "occurred_at": isoformat(self.occurred_at),
                "content": self.content,
                "operation": self.operation.value,
                "schema_version": self.schema_version,
                "metadata": self.metadata,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LineageRecord:
    trace_id: str
    event_id: str
    stage: str
    input_ids: tuple[str, ...]
    output_ids: tuple[str, ...]
    processor_version: str
    processed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

