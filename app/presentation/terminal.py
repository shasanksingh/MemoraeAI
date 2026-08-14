"""Readable terminal presentation that keeps GraphRAG internals in audit logs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.observability.query_log import AuditLogReceipt


class TerminalRenderer:
    """Render user answers, quality, and a compact trace summary."""

    def render_answer(
        self,
        result: dict[str, Any],
        *,
        receipt: AuditLogReceipt | None = None,
        show_trace_summary: bool = False,
    ) -> str:
        reasoning = result.get("reasoning", {})
        quality = reasoning.get("context_quality", {})
        validation = reasoning.get("claim_validation", {})
        claims = reasoning.get("supported_claims", [])
        score = float(quality.get("score", 0.0))
        confidence = "High" if score >= 0.75 else "Medium" if score >= 0.55 else "Limited"
        lines = [
            "MEMORAE",
            f"Question: {result.get('query', '')}",
            "",
            str(result.get("answer", "No answer available.")),
            "",
            f"Confidence: {confidence}  |  Context quality: {score:.0%}",
            f"Support: {len(claims)} verified finding(s) from {validation.get('validated_evidence', 0)} evidence item(s)",
        ]
        if show_trace_summary:
            trace = reasoning.get("retrieval_trace", {})
            rounds = trace.get("rounds", [])
            explored = max((int(item.get("candidate_count", 0)) for item in rounds), default=0)
            layers = trace.get("selected_memory_layers", [])
            lines.extend(
                [
                    "",
                    "Retrieval summary:",
                    f"- {len(rounds)} retrieval round(s), {explored} candidate(s) explored",
                    f"- Memory views used: {', '.join(str(item).replace('_', ' ') for item in layers)}",
                    f"- Stopped because: {trace.get('stop_reason', 'not reported')}",
                ]
            )
        if receipt:
            lines.extend(["", f"Full audit log: {receipt.path}", f"Trace ID: {receipt.trace_id}"])
        return "\n".join(lines)

    def render_many(
        self,
        results: Sequence[dict[str, Any]],
        receipts: Sequence[AuditLogReceipt | None],
        *,
        show_trace_summary: bool = False,
    ) -> str:
        sections = [
            self.render_answer(result, receipt=receipt, show_trace_summary=show_trace_summary)
            for result, receipt in zip(results, receipts, strict=True)
        ]
        return "\n\n".join(sections) if sections else "No results."

    @staticmethod
    def render_snapshot(snapshot: dict[str, Any], log_path: Path | None = None) -> str:
        counts = snapshot.get("counts", {})
        quality = snapshot.get("data_quality", {})
        lines = [
            "MEMORAE PLATFORM STATUS",
            f"Snapshot: {snapshot.get('as_of')}",
            f"Data quality: {float(quality.get('score', 0.0)):.0%}",
            "",
            f"Events: {counts.get('episodes', 0):,}",
            f"Open commitments: {counts.get('open_commitments', 0):,}",
            f"Projects: {counts.get('projects', 0):,}",
            f"Relationships: {counts.get('relationships', 0):,}",
            f"Knowledge graph: {counts.get('graph_nodes', 0):,} nodes / {counts.get('graph_edges', 0):,} edges",
        ]
        if log_path:
            lines.extend(["", f"Operational log: {log_path}"])
        return "\n".join(lines)
