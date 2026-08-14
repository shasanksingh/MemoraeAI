"""Event sourcing, lineage, incremental processing, and data-quality primitives."""

from app.data_engineering.models import CDCOperation, EventEnvelope, LineageRecord
from app.data_engineering.pipeline import IncrementalEventProcessor, ProcessingResult
from app.data_engineering.quality import DataQualityMonitor, DataQualityReport
from app.data_engineering.lakehouse import DataContract, DataZone, LakeRecord, PersonalDataLake
from app.data_engineering.stream import InMemoryEventStream

__all__ = [
    "CDCOperation",
    "DataQualityMonitor",
    "DataQualityReport",
    "DataContract",
    "DataZone",
    "EventEnvelope",
    "IncrementalEventProcessor",
    "InMemoryEventStream",
    "LakeRecord",
    "LineageRecord",
    "ProcessingResult",
    "PersonalDataLake",
]
