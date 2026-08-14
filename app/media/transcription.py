"""Remote transcription contracts and a Deepgram API implementation."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class MediaAsset:
    id: str
    media_type: str
    observed_at: datetime
    source: str
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    speaker: str | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str
    segments: tuple[TranscriptSegment, ...]
    provider: str
    provider_request_id: str | None = None
    language: str | None = None


class TranscriptionProvider(Protocol):
    name: str

    def transcribe_bytes(self, content: bytes, media_type: str) -> TranscriptionResult: ...

    def transcribe_uri(self, uri: str) -> TranscriptionResult: ...


class DeepgramTranscriptionProvider:
    """Use Deepgram's hosted transcription; no local speech model is loaded."""

    name = "deepgram-api"

    def __init__(self, api_key: str, endpoint: str = "https://api.deepgram.com/v1/listen", timeout: float = 120.0) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout = timeout

    def _request(self, body: bytes, content_type: str) -> TranscriptionResult:
        separator = "&" if "?" in self.endpoint else "?"
        url = f"{self.endpoint}{separator}smart_format=true&diarize=true&punctuate=true"
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": content_type,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            request_id = response.headers.get("dg-request-id")
        alternative = payload["results"]["channels"][0]["alternatives"][0]
        words = alternative.get("words", [])
        segments = tuple(
            TranscriptSegment(
                text=str(word.get("punctuated_word") or word.get("word") or ""),
                start_seconds=word.get("start"),
                end_seconds=word.get("end"),
                speaker=str(word.get("speaker")) if word.get("speaker") is not None else None,
                confidence=word.get("confidence"),
            )
            for word in words
        )
        return TranscriptionResult(
            text=str(alternative.get("transcript", "")),
            segments=segments,
            provider=self.name,
            provider_request_id=request_id,
            language=payload.get("results", {}).get("channels", [{}])[0].get("detected_language"),
        )

    def transcribe_bytes(self, content: bytes, media_type: str) -> TranscriptionResult:
        return self._request(content, media_type)

    def transcribe_uri(self, uri: str) -> TranscriptionResult:
        return self._request(json.dumps({"url": uri}).encode("utf-8"), "application/json")

