"""Low-footprint embeddings with an optional remote API backend."""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from collections.abc import Sequence
from typing import Protocol

from app.utils.text import tokenize


class Embedder(Protocol):
    name: str

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / (left_norm * right_norm)))


class HashingEmbedder:
    """Tiny deterministic fallback that keeps retrieval functional without APIs.

    This is a feature-hashing relevance signal, not a semantic-model substitute.
    It downloads nothing and writes no model cache.
    """

    name = "feature-hashing"

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            tokens = tokenize(text)
            features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
            vector = [0.0] * self.dimension
            for feature in features:
                digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] & 1 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class RemoteEmbedder:
    """OpenAI-compatible embedding API adapter with no local model artifacts."""

    def __init__(self, endpoint: str, api_key: str, model: str, timeout_seconds: float = 20.0) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.name = f"remote:{model}"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": list(texts)}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        ordered = sorted(result["data"], key=lambda item: item.get("index", 0))
        return [list(map(float, item["embedding"])) for item in ordered]

