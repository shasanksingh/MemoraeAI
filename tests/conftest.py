"""Shared deterministic test fixtures."""

from __future__ import annotations

import pytest

from app.main import MemoryIntelligenceSystem
from app.retrieval.embeddings import HashingEmbedder


@pytest.fixture(scope="session")
def system() -> MemoryIntelligenceSystem:
    return MemoryIntelligenceSystem.from_json(embedder=HashingEmbedder())
