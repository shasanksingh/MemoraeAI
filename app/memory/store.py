"""Transactional SQLite persistence for materialized memory snapshots."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from app.data_engineering.models import LineageRecord
from app.memory.models import Commitment, Event, Project, SemanticFact
from app.utils.time import isoformat


class SQLiteSnapshotStore:
    """Persist all memory layers in a portable, inspectable SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshot_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                signals_json TEXT NOT NULL,
                source_event_id TEXT,
                lineage_trace_id TEXT,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ingestion_lineage (
                trace_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                input_ids_json TEXT NOT NULL,
                output_ids_json TEXT NOT NULL,
                processor_version TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                PRIMARY KEY (trace_id, stage, event_id)
            );
            CREATE TABLE IF NOT EXISTS commitments (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS semantic_facts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp);
            CREATE INDEX IF NOT EXISTS idx_episodes_source ON episodes(source);
            CREATE INDEX IF NOT EXISTS idx_lineage_event ON ingestion_lineage(event_id);
            CREATE INDEX IF NOT EXISTS idx_facts_project ON semantic_facts(project_id);
            """
        )

    def save(
        self,
        *,
        as_of: str,
        events: Iterable[Event],
        commitments: Iterable[Commitment],
        projects: Iterable[Project],
        facts: Iterable[SemanticFact],
        lineage: Iterable[LineageRecord] = (),
    ) -> None:
        """Atomically replace the materialized point-in-time snapshot."""

        with self._connect() as connection:
            self._schema(connection)
            for table in ("episodes", "commitments", "projects", "semantic_facts", "ingestion_lineage"):
                connection.execute(f"DELETE FROM {table}")  # table names are a fixed internal tuple
            connection.execute(
                "INSERT OR REPLACE INTO snapshot_metadata(key, value) VALUES ('as_of', ?)",
                (as_of,),
            )
            connection.executemany(
                """INSERT INTO episodes(
                    id, timestamp, source, content, signals_json,
                    source_event_id, lineage_trace_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        event.id,
                        isoformat(event.timestamp),
                        event.source,
                        event.content,
                        json.dumps(event.signals.to_dict(), ensure_ascii=False),
                        event.source_event_id,
                        event.lineage_trace_id,
                        json.dumps(event.metadata, ensure_ascii=False),
                    )
                    for event in events
                ),
            )
            connection.executemany(
                "INSERT INTO commitments(id, payload_json) VALUES (?, ?)",
                ((item.id, json.dumps(item.to_dict(), ensure_ascii=False)) for item in commitments),
            )
            connection.executemany(
                "INSERT INTO projects(id, payload_json) VALUES (?, ?)",
                ((project.id, json.dumps(project.to_dict(), ensure_ascii=False)) for project in projects),
            )
            connection.executemany(
                "INSERT INTO semantic_facts(id, project_id, payload_json) VALUES (?, ?, ?)",
                ((fact.id, fact.project_id, json.dumps(fact.to_dict(), ensure_ascii=False)) for fact in facts),
            )
            connection.executemany(
                """INSERT INTO ingestion_lineage(
                    trace_id, event_id, stage, input_ids_json, output_ids_json,
                    processor_version, processed_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        item.trace_id,
                        item.event_id,
                        item.stage,
                        json.dumps(item.input_ids),
                        json.dumps(item.output_ids),
                        item.processor_version,
                        isoformat(item.processed_at),
                        json.dumps(item.metadata, ensure_ascii=False),
                    )
                    for item in lineage
                ),
            )

    def counts(self) -> dict[str, int]:
        """Return row counts for operational checks."""

        with self._connect() as connection:
            self._schema(connection)
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("episodes", "commitments", "projects", "semantic_facts", "ingestion_lineage")
            }
