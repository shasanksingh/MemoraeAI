"""Small, deterministic text utilities used across memory layers."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable

STOPWORDS = {
    "a", "about", "after", "all", "an", "and", "are", "as", "at", "be", "before",
    "but", "by", "can", "do", "for", "from", "has", "have", "i", "if", "in", "is",
    "it", "just", "me", "my", "need", "not", "of", "on", "or", "our", "please", "so",
    "that", "the", "this", "to", "was", "we", "will", "with", "you", "your", "now",
    "still", "said", "send", "before", "later", "earlier", "apr", "aug", "ist", "shashank",
}


def tokenize(text: str, *, remove_stopwords: bool = False) -> list[str]:
    """Tokenize text into lowercase alphanumeric terms."""

    tokens = re.findall(r"[a-z0-9$]+(?:\.[0-9]+)?", text.lower())
    if remove_stopwords:
        return [token for token in tokens if token not in STOPWORDS and len(token) > 1 and not token.isdigit()]
    return tokens


def normalize_text(text: str) -> str:
    """Normalize text for exact and near-duplicate comparisons."""

    return " ".join(tokenize(text))


def jaccard(left: str | Iterable[str], right: str | Iterable[str]) -> float:
    """Return set Jaccard similarity."""

    a = set(tokenize(left, remove_stopwords=True) if isinstance(left, str) else left)
    b = set(tokenize(right, remove_stopwords=True) if isinstance(right, str) else right)
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def top_terms(texts: Iterable[str], limit: int = 4) -> list[str]:
    """Extract corpus terms using frequency with a mild specificity bonus."""

    documents = [set(tokenize(text, remove_stopwords=True)) for text in texts]
    counts = Counter(token for document in documents for token in document)
    total = max(1, len(documents))
    scored = {
        term: frequency * (1.0 + math.log((total + 1) / (1 + sum(term in d for d in documents))))
        for term, frequency in counts.items()
        if len(term) > 2
    }
    return [term for term, _ in sorted(scored.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def concise_title(text: str, limit: int = 90) -> str:
    """Remove transport metadata and return a readable action title."""

    cleaned = re.sub(r"^#[\w-]+\s+", "", text.strip())
    # Speaker prefixes cannot start with a digit, which prevents a clock such
    # as ``18:00 IST`` from being mistaken for transport metadata.
    cleaned = re.sub(r"^[A-Za-z][A-Za-z .<>@-]{0,60}:\s*", "", cleaned)
    cleaned = re.sub(r"^(please\s+|need to\s+|friendly nudge on\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3].rstrip() + "..."


def estimate_tokens(text: str) -> int:
    """Conservative dependency-free token estimate."""

    return max(1, math.ceil(len(text) / 3.7))
