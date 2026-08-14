"""Command-line interface for the Memorae Personal Intelligence Platform."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.config import Settings, StoragePaths, project_root
from app.main import MemoryIntelligenceSystem
from app.observability.query_log import (
    AuditLogReceipt,
    CommandOutputLogger,
    QueryAuditLogger,
    configure_file_logging,
)
from app.presentation.terminal import TerminalRenderer
from app.utils.time import parse_timestamp

DEMO_QUERIES = (
    "Which obligation is most likely to slip?",
    "Who are we waiting on?",
    "What changed about the licensing estimate?",
    "Summarize everything related to the UIE proposal.",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evidence-first personal intelligence and GraphRAG")
    parser.add_argument("--data", type=Path, default=Settings.default_data_path())
    parser.add_argument("--as-of", default="2026-04-13T03:00:00Z")
    parser.add_argument("--storage-root", type=Path, default=project_root() / "storage")
    parser.add_argument("--init-storage", action="store_true", help="Create the project-local storage layout")
    parser.add_argument("--query", help="Question to answer from personal evidence")
    parser.add_argument("--demo", action="store_true", help="Run representative GraphRAG queries")
    parser.add_argument("--snapshot", action="store_true", help="Inspect materialized memories and graph counts")
    parser.add_argument("--trace", action="store_true", help="Show a compact retrieval summary; full trace is logged")
    parser.add_argument("--output", type=Path, help="Write output to an explicit path")
    parser.add_argument("--db", type=Path, help="Persist snapshot and graph to explicit SQLite paths")
    parser.add_argument(
        "--format",
        choices=("pretty", "json"),
        default="pretty",
        help="Choose the export format. JSON is saved to logs/output unless --stdout-json is set.",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print raw JSON to stdout. Intended for scripts; normal users should omit this.",
    )
    parser.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser.parse_args()


def _command_name(args: argparse.Namespace) -> str:
    if args.snapshot:
        return "snapshot"
    if args.demo:
        return "demo"
    return "query"


def _platform_summary(system: MemoryIntelligenceSystem) -> dict[str, Any]:
    snapshot = system.snapshot()
    return {
        "as_of": snapshot["as_of"],
        "counts": snapshot["counts"],
        "data_quality": snapshot["data_quality"],
        "retrieval_backend": snapshot["retrieval_backend"],
        "storage_root": snapshot["storage_root"],
    }


def _resolve_project_storage(root: Path) -> Path:
    resolved_root = root.resolve() if root.is_absolute() else (project_root() / root).resolve()
    resolved_project = project_root().resolve()
    try:
        resolved_root.relative_to(resolved_project)
    except ValueError as exc:
        raise ValueError(f"Storage root must stay inside the project folder: {resolved_project}") from exc
    return resolved_root


def _configure_runtime(args: argparse.Namespace, level: int) -> tuple[Settings, Path, list[str]]:
    settings = Settings(
        as_of=parse_timestamp(args.as_of),
        storage=StoragePaths.from_root(_resolve_project_storage(args.storage_root)),
    )
    settings.prepare_runtime_storage()
    operational_log = configure_file_logging(settings.storage.logs, level)
    return settings, operational_log, []


def _append_footer(
    rendered: str,
    *,
    run_log_path: Path,
    run_id: str,
    notices: list[str],
    exported_path: Path | None = None,
    json_saved_to_run_log: bool = False,
) -> str:
    lines = [rendered.rstrip()]
    footer: list[str] = []
    if exported_path:
        footer.append(f"Exported output: {exported_path}")
    if json_saved_to_run_log:
        footer.append("Structured JSON: saved inside the run log below")
    footer.extend([f"Run log: {run_log_path}", f"Run ID: {run_id}"])
    if notices:
        footer.append("Notice:")
        footer.extend(f"- {notice}" for notice in notices)
    lines.extend(["", *footer])
    return "\n".join(lines)


def _render_requested_output(
    *,
    args: argparse.Namespace,
    result: object,
    renderer: TerminalRenderer,
    receipts: list[AuditLogReceipt | None],
    operational_log: Path,
) -> tuple[str, str]:
    if isinstance(result, list):
        pretty = renderer.render_many(result, receipts, show_trace_summary=args.trace)
    elif isinstance(result, dict):
        pretty = renderer.render_snapshot(result, operational_log)
    else:
        pretty = str(result)
    requested = json.dumps(result, indent=2, ensure_ascii=False) if args.format == "json" else pretty
    return pretty, requested


def main() -> int:
    args = parse_args()
    if args.stdout_json:
        args.format = "json"
    level = getattr(logging, args.log_level)
    logging.getLogger().handlers.clear()
    settings, operational_log, notices = _configure_runtime(args, level)
    audit_logger = QueryAuditLogger(settings.storage.logs)
    command_logger = CommandOutputLogger(settings.storage.logs)
    command_receipt = command_logger.prepare_receipt()
    renderer = TerminalRenderer()
    system = MemoryIntelligenceSystem.from_json(args.data, settings=settings)
    if args.db:
        system.persist(args.db)
    if args.snapshot:
        result: object = system.snapshot()
    else:
        queries = DEMO_QUERIES if args.demo else ((args.query,) if args.query else ())
        if not queries:
            raise SystemExit("Provide --query, --demo, or --snapshot")
        result = [system.answer_query(query) for query in queries]

    platform_summary = _platform_summary(system)
    if isinstance(result, list):
        receipts: list[AuditLogReceipt | None] = []
        for answer in result:
            try:
                receipts.append(
                    audit_logger.record(
                        answer,
                        command=_command_name(args),
                        platform_summary=platform_summary,
                    )
                )
            except OSError as exc:
                notices.append(f"Could not append query audit log: {exc.__class__.__name__}: {exc}")
                receipts.append(None)
    else:
        receipts = []

    pretty_output, requested_output = _render_requested_output(
        args=args,
        result=result,
        renderer=renderer,
        receipts=receipts,
        operational_log=operational_log,
    )

    exported_path: Path | None = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(requested_output + "\n", encoding="utf-8")
        exported_path = args.output

    if args.stdout_json:
        base_terminal_output = requested_output if args.format == "json" else json.dumps(result, indent=2, ensure_ascii=False)
        json_saved_to_run_log = False
    else:
        base_terminal_output = pretty_output
        json_saved_to_run_log = args.format == "json" and exported_path is None

    if args.stdout_json:
        terminal_output = base_terminal_output
    else:
        terminal_output = _append_footer(
            base_terminal_output,
            run_log_path=command_receipt.path,
            run_id=command_receipt.trace_id,
            notices=notices,
            exported_path=exported_path,
            json_saved_to_run_log=json_saved_to_run_log,
        )
    try:
        command_logger.record(
            command_receipt,
            command=_command_name(args),
            requested_format=args.format,
            result=result,
            terminal_output=terminal_output,
            audit_receipts=[receipt for receipt in receipts if receipt is not None],
            platform_summary=platform_summary,
            notices=notices,
        )
    except OSError as exc:
        if not args.stdout_json:
            terminal_output = _append_footer(
                base_terminal_output,
                run_log_path=command_receipt.path,
                run_id=command_receipt.trace_id,
                notices=[*notices, f"Could not write command output log: {exc.__class__.__name__}: {exc}"],
                exported_path=exported_path,
                json_saved_to_run_log=json_saved_to_run_log,
            )
    print(terminal_output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(
            "Memorae could not complete the command.\n"
            f"Reason: {exc.__class__.__name__}: {exc}\n"
            "Tip: make sure the project storage folder is writable, or pass --storage-root to a folder inside this project.",
            file=sys.stderr,
        )
        raise SystemExit(1)
