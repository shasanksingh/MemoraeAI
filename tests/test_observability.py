"""Friendly presentation and complete structured audit logging."""

import json

from app.observability.query_log import CommandOutputLogger, QueryAuditLogger
from app.presentation.terminal import TerminalRenderer


def test_audit_logger_stores_full_trace_and_terminal_hides_ids(system, tmp_path) -> None:
    result = system.answer_query("Who are we waiting on?")
    receipt = QueryAuditLogger(tmp_path / "logs").record(result)
    rendered = TerminalRenderer().render_answer(result, receipt=receipt, show_trace_summary=True)
    assert "Full audit log:" in rendered
    assert "Retrieval summary:" in rendered
    assert "expansion_paths" not in rendered
    assert "new_event_ids" not in rendered
    payload = json.loads(receipt.path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["reasoning"]["retrieval_trace"]["expansion_paths"]
    assert payload["selected_context"]
    assert payload["trace_id"] == receipt.trace_id


def test_friendly_renderer_reports_quality_and_support(system) -> None:
    result = system.answer_query("What changed about the licensing estimate?")
    rendered = TerminalRenderer().render_answer(result)
    assert "Context quality:" in rendered
    assert "verified finding" in rendered
    assert "[evidence:" not in rendered
    assert "$48.5k" in rendered


def test_command_output_logger_stores_raw_result_and_terminal_copy(system, tmp_path) -> None:
    result = system.answer_query("Who are we waiting on?")
    logger = CommandOutputLogger(tmp_path / "logs")
    receipt = logger.prepare_receipt()
    terminal_output = TerminalRenderer().render_answer(result)
    logger.record(
        receipt,
        command="query",
        requested_format="json",
        result=[result],
        terminal_output=terminal_output,
        notices=["structured JSON saved to run log"],
    )
    payload = json.loads(receipt.path.read_text(encoding="utf-8"))
    assert payload["trace_id"] == receipt.trace_id
    assert payload["requested_format"] == "json"
    assert payload["terminal_output"] == terminal_output
    assert payload["result"][0]["reasoning"]["retrieval_trace"]["expansion_paths"]
