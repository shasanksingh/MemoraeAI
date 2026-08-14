"""Voice-note, meeting-audio, and call-processing pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.media.transcription import MediaAsset, TranscriptSegment, TranscriptionProvider, TranscriptionResult
from app.utils.time import isoformat


@dataclass(frozen=True, slots=True)
class MediaPipelineResult:
    status: str
    asset_id: str
    transcript: TranscriptionResult | None
    event_records: tuple[dict[str, Any], ...]
    message: str


class VoicePipeline:
    """Transcribe remotely or accept a sidecar transcript, then emit events."""

    def __init__(
        self,
        provider: TranscriptionProvider | None = None,
        event_sink: Callable[[list[dict[str, Any]]], object] | None = None,
    ) -> None:
        self.provider = provider
        self.event_sink = event_sink

    def process(
        self,
        asset: MediaAsset,
        *,
        content: bytes | None = None,
        transcript_text: str | None = None,
    ) -> MediaPipelineResult:
        if transcript_text is not None:
            transcript = TranscriptionResult(
                text=transcript_text,
                segments=(TranscriptSegment(transcript_text),),
                provider="supplied-transcript",
            )
        elif self.provider is not None and content is not None:
            transcript = self.provider.transcribe_bytes(content, asset.media_type)
        elif self.provider is not None and asset.uri:
            transcript = self.provider.transcribe_uri(asset.uri)
        else:
            return MediaPipelineResult(
                "pending_transcription",
                asset.id,
                None,
                (),
                "No API provider or transcript was supplied; media metadata remains available for later processing.",
            )
        record = {
            "id": f"media:{asset.id}",
            "timestamp": isoformat(asset.observed_at),
            "source": asset.source or "voice_note",
            "content": transcript.text,
            "media_asset_id": asset.id,
            "media_type": asset.media_type,
            "transcription_provider": transcript.provider,
            "provider_request_id": transcript.provider_request_id,
            "segment_count": len(transcript.segments),
            **asset.metadata,
        }
        if self.event_sink:
            self.event_sink([record])
        return MediaPipelineResult("processed", asset.id, transcript, (record,), "Transcript emitted to ingestion.")

