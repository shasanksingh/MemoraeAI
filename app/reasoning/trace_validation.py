"""Mechanical validation of evidence provenance and retrieval traces."""

from __future__ import annotations

from datetime import datetime

from app.retrieval.graphrag import GraphRetrievalResult


class ReasoningTraceValidator:
    def validate(
        self,
        result: GraphRetrievalResult,
        context: list[dict[str, object]],
        claim_evidence: list[tuple[str, list[str]]],
        *,
        as_of: datetime,
    ) -> dict[str, object]:
        errors: list[str] = []
        selected_ids = {str(item.get("id")) for item in context}
        if not result.rounds or result.rounds[0].operation != "parallel sparse/vector broad recall":
            errors.append("trace does not begin with broad evidence recall")
        for item in context:
            timestamp = item.get("timestamp")
            if timestamp and str(timestamp) > as_of.isoformat().replace("+00:00", "Z"):
                errors.append(f"future evidence selected: {item.get('id')}")
        for claim, evidence_ids in claim_evidence:
            if not evidence_ids:
                errors.append(f"unsupported claim: {claim}")
            missing = set(evidence_ids) - selected_ids
            if missing:
                errors.append(f"claim evidence absent from context: {sorted(missing)}")
        return {
            "valid": not errors,
            "errors": errors,
            "validated_claims": len(claim_evidence),
            "validated_evidence": len(selected_ids),
        }

