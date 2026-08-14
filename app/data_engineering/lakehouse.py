"""Low-footprint medallion data lake stored under the centralized D drive."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class DataZone(str, Enum):
    RAW = "raw"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    KNOWLEDGE = "knowledge"
    INTELLIGENCE = "intelligence"


@dataclass(frozen=True, slots=True)
class DataContract:
    name: str
    version: str
    required_fields: tuple[str, ...]

    def validate(self, payload: dict[str, Any]) -> tuple[str, ...]:
        return tuple(field_name for field_name in self.required_fields if payload.get(field_name) is None)


@dataclass(frozen=True, slots=True)
class LakeRecord:
    id: str
    zone: DataZone
    payload: dict[str, Any]
    source_ids: tuple[str, ...]
    contract: str
    contract_version: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PersonalDataLake:
    """Append JSONL zone records with explicit contracts and source lineage."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def append(self, record: LakeRecord) -> Path:
        zone = self.root / record.zone.value
        zone.mkdir(parents=True, exist_ok=True)
        path = zone / f"{record.created_at:%Y-%m}.jsonl"
        payload = {
            "id": record.id,
            "zone": record.zone.value,
            "payload": record.payload,
            "source_ids": record.source_ids,
            "contract": record.contract,
            "contract_version": record.contract_version,
            "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
        }
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        return path

    def promote(
        self,
        record: LakeRecord,
        target: DataZone,
        contract: DataContract,
        transform: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> LakeRecord:
        payload = transform(record.payload)
        missing = contract.validate(payload)
        if missing:
            raise ValueError(f"{contract.name} missing required fields: {', '.join(missing)}")
        promoted = LakeRecord(
            id=uuid.uuid4().hex,
            zone=target,
            payload=payload,
            source_ids=(record.id, *record.source_ids),
            contract=contract.name,
            contract_version=contract.version,
        )
        self.append(promoted)
        return promoted

