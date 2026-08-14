"""Privacy-conscious query audit logs stored in project-local runtime storage."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditLogReceipt:
    trace_id: str
    path: Path
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class CommandOutputReceipt:
    trace_id: str
    path: Path
    recorded_at: datetime


class QueryAuditLogger:
    """Append complete query results as JSONL without printing internals to users."""

    schema_version = "query-audit/1.0"

    def __init__(self, log_directory: str | Path) -> None:
        self.log_directory = Path(log_directory)

    def record(
        self,
        result: dict[str, Any],
        *,
        command: str = "query",
        platform_summary: dict[str, Any] | None = None,
    ) -> AuditLogReceipt:
        self.log_directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        trace_id = uuid.uuid4().hex
        path = self.log_directory / f"query-audit-{now:%Y-%m-%d}.jsonl"
        payload = {
            "schema_version": self.schema_version,
            "trace_id": trace_id,
            "recorded_at": now.isoformat().replace("+00:00", "Z"),
            "command": command,
            "query": result.get("query"),
            "user_answer": result.get("answer"),
            "selected_context": result.get("selected_context", []),
            "reasoning": result.get("reasoning", {}),
            "platform_summary": platform_summary or {},
        }
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        return AuditLogReceipt(trace_id, path, now)


class CommandOutputLogger:
    """Store complete command output artifacts while keeping stdout readable."""

    schema_version = "command-output/1.0"

    def __init__(self, log_directory: str | Path) -> None:
        self.log_directory = Path(log_directory)

    def prepare_receipt(self) -> CommandOutputReceipt:
        self.log_directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        trace_id = uuid.uuid4().hex
        path = self.log_directory / f"command-output-{now:%Y%m%d-%H%M%S}-{trace_id[:8]}.json"
        return CommandOutputReceipt(trace_id=trace_id, path=path, recorded_at=now)

    def record(
        self,
        receipt: CommandOutputReceipt,
        *,
        command: str,
        requested_format: str,
        result: Any,
        terminal_output: str,
        audit_receipts: list[AuditLogReceipt] | None = None,
        platform_summary: dict[str, Any] | None = None,
        notices: list[str] | None = None,
    ) -> CommandOutputReceipt:
        self.log_directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.schema_version,
            "trace_id": receipt.trace_id,
            "recorded_at": receipt.recorded_at.isoformat().replace("+00:00", "Z"),
            "command": command,
            "requested_format": requested_format,
            "terminal_output": terminal_output,
            "result": result,
            "audit_receipts": [
                {
                    "trace_id": item.trace_id,
                    "path": str(item.path),
                    "recorded_at": item.recorded_at.isoformat().replace("+00:00", "Z"),
                }
                for item in audit_receipts or []
            ],
            "platform_summary": platform_summary or {},
            "notices": notices or [],
        }
        receipt.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return receipt


def configure_file_logging(log_directory: str | Path, level: int = logging.INFO) -> Path:
    """Configure a bounded operational log under the project-local storage root."""

    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "platform.log"
    root = logging.getLogger()
    if not any(isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(path) for handler in root.handlers):
        handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)
    return path
