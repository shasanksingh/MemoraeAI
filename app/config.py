"""Runtime and storage configuration for the Personal Intelligence Platform."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.utils.time import parse_timestamp


@dataclass(frozen=True, slots=True)
class StoragePaths:
    """Project-local storage paths. No runtime data is written outside the repository."""

    root: Path
    embeddings: Path
    sqlite: Path
    database: Path
    graph: Path
    logs: Path
    indexes: Path
    temp: Path
    cache: Path
    lake: Path
    uploads: Path
    exports: Path
    models: Path
    artifacts: Path
    generated: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "StoragePaths":
        base = Path(root)
        return cls(
            root=base,
            embeddings=base / "embeddings",
            sqlite=base / "sqlite",
            database=base / "database",
            graph=base / "graph",
            logs=base / "logs",
            indexes=base / "indexes",
            temp=base / "temp",
            cache=base / "cache",
            lake=base / "lake",
            uploads=base / "uploads",
            exports=base / "exports",
            models=base / "models",
            artifacts=base / "artifacts",
            generated=base / "generated",
        )

    def ensure(self) -> None:
        """Create the configured project-local runtime layout."""

        for path in (
            self.root,
            self.embeddings,
            self.sqlite,
            self.database,
            self.graph,
            self.logs,
            self.indexes,
            self.temp,
            self.cache,
            self.lake,
            self.uploads,
            self.exports,
            self.models,
            self.artifacts,
            self.generated,
        ):
            path.mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_storage() -> StoragePaths:
    return StoragePaths.from_root(os.getenv("MEMORAE_STORAGE_ROOT", project_root() / "storage"))


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration shared by ingestion, graph, retrieval, and intelligence layers."""

    as_of: datetime = parse_timestamp("2026-08-13T03:00:00Z")
    storage: StoragePaths = field(default_factory=_default_storage)
    embedding_dimension: int = 384
    candidate_pool_size: int = 80
    retrieval_k: int = 16
    max_expansion_rounds: int = 3
    max_expanded_events: int = 500
    graph_max_hops: int = 2
    temporal_neighbor_count: int = 3
    context_token_budget: int = 4_000
    near_duplicate_threshold: float = 0.88
    min_context_quality: float = 0.55

    @staticmethod
    def default_data_path() -> Path:
        return project_root() / "data" / "memorae_mock_events.json"

    def prepare_runtime_storage(self) -> None:
        """Create storage and redirect temporary/cache/model paths into the project."""

        self.storage.ensure()
        os.environ["TMP"] = str(self.storage.temp)
        os.environ["TEMP"] = str(self.storage.temp)
        os.environ["XDG_CACHE_HOME"] = str(self.storage.cache)
        os.environ["HF_HOME"] = str(self.storage.models / "huggingface")
        os.environ["TRANSFORMERS_CACHE"] = str(self.storage.models / "huggingface" / "transformers")
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(self.storage.models / "sentence-transformers")
        os.environ["TORCH_HOME"] = str(self.storage.models / "torch")
