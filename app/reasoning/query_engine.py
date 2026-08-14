"""Evidence-first answer construction over one GraphRAG workflow."""

from __future__ import annotations

from datetime import datetime

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType, RelationType
from app.memory.models import QueryAnswer, RetrievalHit
from app.reasoning.evidence_context import EvidenceContextAssembler
from app.reasoning.trace_validation import ReasoningTraceValidator
from app.retrieval.graphrag import GraphRAGRetriever, GraphRetrievalResult
from app.utils.text import tokenize
from app.utils.time import IST, isoformat, parse_timestamp


class QueryEngine:
    """Retrieve first, then construct only claims supported by selected evidence."""

    _claim_types = {
        NodeType.TASK,
        NodeType.MEETING,
        NodeType.DECISION,
        NodeType.DEADLINE,
        NodeType.RISK,
        NodeType.DEPENDENCY,
        NodeType.PREFERENCE,
        NodeType.PROJECT,
        NodeType.DOCUMENT,
        NodeType.GOAL,
        NodeType.LEARNING,
        NodeType.TOPIC,
    }

    def __init__(
        self,
        retriever: GraphRAGRetriever,
        graph: EvidenceGraph,
        context_builder: EvidenceContextAssembler,
        as_of: datetime,
        *,
        future_events_excluded: int = 0,
        validator: ReasoningTraceValidator | None = None,
    ) -> None:
        self.retriever = retriever
        self.graph = graph
        self.context_builder = context_builder
        self.as_of = as_of
        self.future_events_excluded = future_events_excluded
        self.validator = validator or ReasoningTraceValidator()

    def _node_score(self, node: GraphNode, result: GraphRetrievalResult) -> float:
        query_terms = set(result.plan.query_terms)
        label_terms = set(tokenize(node.label, remove_stopwords=True))
        overlap = len(query_terms & label_terms) / max(1, len(query_terms))
        facet = 0.0
        requested = set(result.plan.requested_relations)
        for edge, _ in self.graph.adjacent(node.id):
            if edge.relation in requested:
                facet = max(facet, edge.confidence)
        if "priority" in result.plan.requested_facets and node.node_type is NodeType.TASK:
            facet = max(
                facet,
                0.4 * float(node.attributes.get("urgency", 0.0))
                + 0.35 * float(node.attributes.get("risk", 0.0))
                + 0.25 * float(node.attributes.get("importance", 0.0)),
            )
        return 0.65 * overlap + 0.35 * facet

    def _claims(
        self,
        result: GraphRetrievalResult,
        selected: list[RetrievalHit],
    ) -> list[tuple[GraphNode, list[str]]]:
        selected_ids = {hit.event.id for hit in selected}
        candidates = [
            node for node in self.graph.nodes()
            if node.node_type in self._claim_types and node.evidence_ids & selected_ids
        ]
        ranked = sorted(candidates, key=lambda node: (-self._node_score(node, result), node.id))
        claims: list[tuple[GraphNode, list[str]]] = []
        normalized: set[str] = set()
        for node in ranked:
            key = " ".join(tokenize(node.label))
            if key in normalized:
                continue
            evidence = sorted(node.evidence_ids & selected_ids)
            if not evidence:
                continue
            normalized.add(key)
            claims.append((node, evidence))
            if len(claims) >= min(10, result.plan.final_limit):
                break
        return claims

    def _render(
        self,
        result: GraphRetrievalResult,
        selected: list[RetrievalHit],
        claims: list[tuple[GraphNode, list[str]]],
    ) -> str:
        groups = {
            "Actions": [],
            "Risks and blockers": [],
            "Decisions and changes": [],
            "Meetings and deadlines": [],
            "Related context": [],
        }
        for node, _ in claims:
            if node.node_type is NodeType.DEADLINE:
                try:
                    local = parse_timestamp(node.label).astimezone(IST)
                    label = local.strftime("%a, %d %b %Y at %I:%M %p IST")
                except ValueError:
                    label = node.label
            else:
                label = node.label.rstrip(" .")
            if node.node_type is NodeType.TASK:
                groups["Actions"].append(label)
            elif node.node_type in {NodeType.RISK, NodeType.DEPENDENCY}:
                groups["Risks and blockers"].append(label)
            elif node.node_type is NodeType.DECISION:
                groups["Decisions and changes"].append(label)
            elif node.node_type in {NodeType.MEETING, NodeType.DEADLINE}:
                groups["Meetings and deadlines"].append(label)
            else:
                groups["Related context"].append(label)

        requested = set(result.plan.requested_relations)
        if RelationType.HAS_RISK in requested or RelationType.BLOCKED_BY in requested:
            order = ["Risks and blockers", "Actions", "Decisions and changes", "Meetings and deadlines", "Related context"]
        elif RelationType.SUPERSEDES in requested:
            order = ["Decisions and changes", "Related context", "Actions", "Risks and blockers", "Meetings and deadlines"]
        elif "priority" in result.plan.requested_facets:
            order = ["Actions", "Risks and blockers", "Meetings and deadlines", "Decisions and changes", "Related context"]
        else:
            order = ["Actions", "Decisions and changes", "Risks and blockers", "Meetings and deadlines", "Related context"]

        lines = ["Here's what I found:"]
        for heading in order:
            items = groups[heading]
            if not items:
                continue
            lines.extend(["", f"{heading}:"])
            lines.extend(f"- {item}" for item in items[:6])
        if not claims:
            for hit in selected[:8]:
                lines.append(f"- {hit.event.content}")
        if not selected:
            lines.append("- No evidence was found for this query at the current snapshot.")
        return "\n".join(lines)

    def answer_query(self, query: str) -> QueryAnswer:
        if not query.strip():
            raise ValueError("query cannot be empty")
        result = self.retriever.retrieve(query)
        selected, context, stats, quality = self.context_builder.assemble(result)
        claims = self._claims(result, selected)
        claim_evidence = [(node.label, evidence) for node, evidence in claims]
        supported_claims = [
            {
                "type": node.node_type.value,
                "text": node.label,
                "evidence_ids": evidence,
            }
            for node, evidence in claims
        ]
        validation = self.validator.validate(result, context, claim_evidence, as_of=self.as_of)
        answer = self._render(result, selected, claims)
        return QueryAnswer(
            query=query,
            answer=answer,
            selected_context=context,
            reasoning={
                "retrieval_trace": result.trace_dict(),
                "context_quality": quality.to_dict(),
                "context_stats": {
                    "input_count": stats.input_count,
                    "duplicates_removed": stats.duplicates_removed,
                    "budget_omissions": stats.budget_omissions,
                    "tokens_used": stats.tokens_used,
                },
                "claim_validation": validation,
                "supported_claims": supported_claims,
                "snapshot": {
                    "as_of": isoformat(self.as_of),
                    "future_events_excluded": self.future_events_excluded,
                },
            },
        )
