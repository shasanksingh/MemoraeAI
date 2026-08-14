"""API-only media ingestion and transcript fallback."""

from app.media.transcription import MediaAsset
from app.media.video import VideoPipeline
from app.media.voice import VoicePipeline
from app.utils.time import parse_timestamp


def _asset(media_type: str = "audio/wav") -> MediaAsset:
    return MediaAsset("note-1", media_type, parse_timestamp("2026-04-01T09:00:00Z"), "voice_note")


def test_voice_pipeline_works_with_supplied_transcript() -> None:
    result = VoicePipeline().process(_asset(), transcript_text="I promised to send the report Friday.")
    assert result.status == "processed"
    assert result.event_records[0]["transcription_provider"] == "supplied-transcript"


def test_voice_pipeline_is_non_fatal_without_api() -> None:
    result = VoicePipeline().process(_asset())
    assert result.status == "pending_transcription"
    assert not result.event_records


def test_video_audio_extraction_is_provider_managed() -> None:
    result = VideoPipeline().process(_asset("video/mp4"), transcript_text="Decision: ship on Tuesday.")
    assert result.event_records[0]["audio_extraction"] == "transcription-provider-managed"

