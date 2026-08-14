"""Meeting-recording pipeline with provider-managed audio extraction."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.media.transcription import MediaAsset, TranscriptionProvider
from app.media.voice import MediaPipelineResult, VoicePipeline


class VideoPipeline:
    """Process Zoom, Meet, Teams, and generic recordings without local models.

    The remote transcription provider receives the video bytes or URI and handles
    audio extraction. Memorae never invokes ffmpeg or creates a local media cache.
    """

    def __init__(
        self,
        provider: TranscriptionProvider | None = None,
        event_sink: Callable[[list[dict[str, Any]]], object] | None = None,
    ) -> None:
        self.voice = VoicePipeline(provider, event_sink)

    def process(
        self,
        asset: MediaAsset,
        *,
        content: bytes | None = None,
        transcript_text: str | None = None,
    ) -> MediaPipelineResult:
        metadata = {**asset.metadata, "audio_extraction": "transcription-provider-managed"}
        normalized = MediaAsset(
            id=asset.id,
            media_type=asset.media_type,
            observed_at=asset.observed_at,
            source=asset.source or "meeting_video",
            uri=asset.uri,
            metadata=metadata,
        )
        return self.voice.process(normalized, content=content, transcript_text=transcript_text)

