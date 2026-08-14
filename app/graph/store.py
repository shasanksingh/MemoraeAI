"""Normalized SQLite persistence for the knowledge graph."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.graph.evidence import EvidenceGraph


class KnowledgeGraphStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, graph: EvidenceGraph) -> dict[str, int]:
        with sqlite3.connect(self.path) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    attributes_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    attributes_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id, relation);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id, relation);
                """
            )
            connection.execute("DELETE FROM graph_nodes")
            connection.execute("DELETE FROM graph_edges")
            connection.executemany(
                "INSERT INTO graph_nodes VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        node.id,
                        node.node_type.value,
                        node.label,
                        json.dumps(sorted(node.evidence_ids)),
                        json.dumps(sorted(node.aliases)),
                        json.dumps(node.attributes, ensure_ascii=False),
                    )
                    for node in graph.nodes()
                ),
            )
            connection.executemany(
                "INSERT INTO graph_edges VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        edge.id,
                        edge.source_id,
                        edge.target_id,
                        edge.relation.value,
                        json.dumps(edge.evidence_ids),
                        edge.confidence,
                        json.dumps(edge.attributes, ensure_ascii=False),
                    )
                    for edge in graph.edges()
                ),
            )
        return {"graph_nodes": len(graph.nodes()), "graph_edges": len(graph.edges())}

