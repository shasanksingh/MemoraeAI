"""Event sourcing, CDC, lineage, and storage-layout behavior."""

from app.config import Settings, project_root
from app.data_engineering.models import CDCOperation, EventEnvelope
from app.data_engineering.pipeline import IncrementalEventProcessor
from app.data_engineering.lakehouse import DataContract, DataZone, LakeRecord, PersonalDataLake
from app.utils.time import parse_timestamp


def test_storage_defaults_to_project_folder() -> None:
    settings = Settings()
    assert settings.storage.root == project_root() / "storage"
    assert "users" not in str(settings.storage.cache).lower()
    assert "personalintelligence" not in str(settings.storage.root).lower()


def test_incremental_processor_deduplicates_and_tracks_checkpoint() -> None:
    observed = parse_timestamp("2026-04-01T09:00:00Z")
    envelope = EventEnvelope(
        event_id="event-1",
        source_event_id="source-1",
        source="voice_note",
        observed_at=observed,
        occurred_at=observed,
        content="I will send the report tomorrow",
        operation=CDCOperation.UPSERT,
        source_cursor="cursor-1",
    )
    processor = IncrementalEventProcessor()
    first = processor.process([envelope], as_of=parse_timestamp("2026-04-02T09:00:00Z"))
    second = processor.process([envelope], as_of=parse_timestamp("2026-04-02T09:00:00Z"))
    assert first.accepted_event_ids == ["event-1"]
    assert first.checkpoints["voice_note"] == "cursor-1"
    assert not second.accepted_event_ids


def test_ingestion_exposes_lineage_and_quality(system) -> None:
    snapshot = system.snapshot()
    assert snapshot["data_quality"]["lineage_records"] == snapshot["counts"]["episodes"]
    assert snapshot["data_quality"]["score"] > 0.7


def test_medallion_lake_promotion_preserves_lineage(tmp_path) -> None:
    lake = PersonalDataLake(tmp_path / "lake")
    raw = LakeRecord("raw-1", DataZone.RAW, {"content": "hello"}, (), "raw", "1")
    lake.append(raw)
    contract = DataContract("bronze-event", "1", ("content", "source"))
    bronze = lake.promote(raw, DataZone.BRONZE, contract, lambda value: {**value, "source": "note"})
    assert bronze.source_ids == ("raw-1",)
    assert (tmp_path / "lake" / "bronze").exists()
