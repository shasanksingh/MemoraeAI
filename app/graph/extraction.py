"""Explainable entity, relationship, and knowledge-graph extraction."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from app.graph.evidence import EvidenceGraph
from app.graph.models import EntityMention, GraphEdge, GraphNode, NodeType, RelationType
from app.memory.models import Event
from app.utils.text import concise_title, tokenize, top_terms
from app.utils.time import isoformat


_NON_ENTITIES = {
    "Apr", "April", "Aug", "August", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "Today", "Tomorrow", "Calendar", "Friendly", "Need",
    "Please", "Updated", "Ignore", "After", "Before", "Northstar Meet",
}


def _entity_id(node_type: NodeType, name: str) -> str:
    normalized = " ".join(tokenize(name))
    digest = hashlib.sha1(f"{node_type.value}|{normalized}".encode()).hexdigest()[:14]
    return f"{node_type.value}-{digest}"


class EntityResolver:
    """Resolve high-precision people, project, organization, and document mentions."""

    _speaker = re.compile(r"^(?:#[\w-]+\s+)?([A-Z][A-Za-z-]+)(?::|\s+to\s+)")
    _named_person = re.compile(r"\b(?:to|with|from|ask|tell|send|waiting on)\s+([A-Z][a-z]{2,})\b")
    _capitalized = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b")
    _acronym = re.compile(r"\b[A-Z][A-Z0-9]{1,7}\b")
    _document = re.compile(
        r"\b([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+){0,3}\s+"
        r"(?:proposal|SOW|report|checklist|appendix|diagram|rubric|FAQ|invoice))\b",
        re.I,
    )

    def extract(self, text: str) -> list[EntityMention]:
        candidates: dict[tuple[NodeType, str], EntityMention] = {}

        def add(match: re.Match[str], node_type: NodeType, confidence: float, group: int = 0) -> None:
            value = match.group(group).strip(" #:.\"")
            if value in _NON_ENTITIES or len(value) < 2:
                return
            start, end = match.span(group)
            key = (node_type, value.lower())
            mention = EntityMention(
                entity_id=_entity_id(node_type, value),
                canonical_name=value,
                node_type=node_type,
                text=value,
                start=start,
                end=end,
                confidence=confidence,
            )
            if key not in candidates or candidates[key].confidence < confidence:
                candidates[key] = mention

        if speaker := self._speaker.search(text):
            add(speaker, NodeType.PERSON, 0.95, 1)
        for match in self._named_person.finditer(text):
            add(match, NodeType.PERSON, 0.82, 1)
        for match in self._acronym.finditer(text):
            value = match.group(0)
            if value not in {"IST", "EOD", "FAQ", "ELT", "SOC2"}:
                add(match, NodeType.PROJECT, 0.84)
        for match in self._document.finditer(text):
            add(match, NodeType.DOCUMENT, 0.82, 1)
        for match in self._capitalized.finditer(text):
            value = match.group(0)
            if value in _NON_ENTITIES or value.isupper():
                continue
            nearby = text[max(0, match.start() - 16): match.end() + 16].lower()
            if any(term in nearby for term in ("project", "proposal", "engine", "sow")):
                add(match, NodeType.PROJECT, 0.68)
        return sorted(candidates.values(), key=lambda item: (item.start, -item.confidence, item.entity_id))


class RelationshipExtractor:
    """Derive auditable graph nodes/edges from one event and resolved entities."""

    _decision = re.compile(r"\b(decid(?:e|ed)|decision|approved|correction|updated|moved from|is now due)\b", re.I)
    _preference = re.compile(r"\b(i prefer|i like|i hate|default me to|please avoid|keep .* clear)\b", re.I)
    _dependency = re.compile(r"\b(?:waiting on|blocked (?:by|on)|depends on|still need)\s+([^,.;]+)", re.I)
    _correction = re.compile(r"\b(ignore .*earlier|correction|do not use the old|updated|now due|moved from)\b", re.I)
    _goal = re.compile(r"\b(my goal is|goal:|i aim to|i want to|objective:|target:)\b", re.I)
    _learning = re.compile(r"\b(i learned|lesson learned|i realized|key takeaway|note to self)\b", re.I)

    def extract(
        self,
        event: Event,
        mentions: list[EntityMention],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        event_node_id = f"event:{event.id}"
        nodes: list[GraphNode] = [
            GraphNode(
                id=event_node_id,
                node_type=NodeType.EVENT,
                label=event.content,
                evidence_ids={event.id},
                attributes={"timestamp": isoformat(event.timestamp), "source": event.source},
            )
        ]
        edges: list[GraphEdge] = []
        for mention in mentions:
            nodes.append(
                GraphNode(
                    id=mention.entity_id,
                    node_type=mention.node_type,
                    label=mention.canonical_name,
                    evidence_ids={event.id},
                    aliases={mention.text},
                    attributes={"link_confidence": mention.confidence},
                )
            )
            edges.append(
                GraphEdge(event_node_id, mention.entity_id, RelationType.MENTIONS, (event.id,), mention.confidence)
            )

        derived: list[GraphNode] = []
        if event.signals.is_task or event.signals.is_commitment:
            derived.append(
                GraphNode(
                    id=f"task:{event.id}",
                    node_type=NodeType.TASK,
                    label=concise_title(event.content, limit=180),
                    evidence_ids={event.id},
                    attributes={
                        "importance": event.signals.importance_score,
                        "urgency": event.signals.urgency_score,
                        "risk": event.signals.risk_score,
                    },
                )
            )
        if event.signals.is_meeting:
            derived.append(
                GraphNode(f"meeting:{event.id}", NodeType.MEETING, concise_title(event.content, limit=180), {event.id})
            )
        if self._decision.search(event.content):
            derived.append(
                GraphNode(f"decision:{event.id}", NodeType.DECISION, concise_title(event.content, limit=180), {event.id})
            )
        if self._preference.search(event.content):
            derived.append(
                GraphNode(f"preference:{event.id}", NodeType.PREFERENCE, concise_title(event.content, limit=180), {event.id})
            )
        if self._goal.search(event.content):
            derived.append(
                GraphNode(f"goal:{event.id}", NodeType.GOAL, concise_title(event.content, limit=180), {event.id})
            )
        if self._learning.search(event.content):
            derived.append(
                GraphNode(f"learning:{event.id}", NodeType.LEARNING, concise_title(event.content, limit=180), {event.id})
            )
        if event.signals.risk_score >= 0.25:
            derived.append(
                GraphNode(
                    f"risk:{event.id}",
                    NodeType.RISK,
                    concise_title(event.content, limit=180),
                    {event.id},
                    attributes={"score": event.signals.risk_score},
                )
            )
        if event.signals.deadline_at:
            derived.append(
                GraphNode(
                    f"deadline:{event.id}",
                    NodeType.DEADLINE,
                    isoformat(event.signals.deadline_at) or "unknown deadline",
                    {event.id},
                )
            )
        if dependency := self._dependency.search(event.content):
            label = dependency.group(1).strip()
            derived.append(
                GraphNode(_entity_id(NodeType.DEPENDENCY, label), NodeType.DEPENDENCY, label, {event.id})
            )

        nodes.extend(derived)
        for node in derived:
            edges.append(GraphEdge(event_node_id, node.id, RelationType.EVIDENCE_FOR, (event.id,), 0.9))
            if node.node_type is NodeType.DEADLINE:
                for task in (item for item in derived if item.node_type in {NodeType.TASK, NodeType.MEETING}):
                    edges.append(GraphEdge(task.id, node.id, RelationType.HAS_DEADLINE, (event.id,), 0.96))
            if node.node_type is NodeType.RISK:
                for task in (item for item in derived if item.node_type is NodeType.TASK):
                    edges.append(GraphEdge(task.id, node.id, RelationType.HAS_RISK, (event.id,), 0.8))
            if node.node_type is NodeType.DEPENDENCY:
                for task in (item for item in derived if item.node_type is NodeType.TASK):
                    edges.append(GraphEdge(task.id, node.id, RelationType.BLOCKED_BY, (event.id,), 0.82))

        projects = [mention for mention in mentions if mention.node_type is NodeType.PROJECT]
        people = [mention for mention in mentions if mention.node_type is NodeType.PERSON]
        if derived and not projects:
            terms = top_terms([event.content], limit=1)
            if terms:
                topic = GraphNode(_entity_id(NodeType.TOPIC, terms[0]), NodeType.TOPIC, terms[0], {event.id})
                nodes.append(topic)
                edges.append(GraphEdge(event_node_id, topic.id, RelationType.MENTIONS, (event.id,), 0.6))
        for node in derived:
            for project in projects:
                if node.node_type is NodeType.MEETING:
                    edges.append(GraphEdge(node.id, project.entity_id, RelationType.DISCUSSES, (event.id,), project.confidence))
                elif node.node_type is NodeType.DECISION:
                    edges.append(GraphEdge(node.id, project.entity_id, RelationType.IMPACTS, (event.id,), project.confidence))
                    edges.append(GraphEdge(project.entity_id, node.id, RelationType.CONTAINS, (event.id,), project.confidence))
                elif node.node_type is NodeType.RISK:
                    edges.append(GraphEdge(project.entity_id, node.id, RelationType.HAS_RISK, (event.id,), project.confidence))
                else:
                    edges.append(GraphEdge(node.id, project.entity_id, RelationType.BELONGS_TO, (event.id,), project.confidence))
            if node.node_type is NodeType.TASK and people:
                owner = people[0]
                edges.append(GraphEdge(owner.entity_id, node.id, RelationType.OWNS, (event.id,), 0.58))
        tasks = [node for node in derived if node.node_type is NodeType.TASK]
        decisions = [node for node in derived if node.node_type is NodeType.DECISION]
        for decision in decisions:
            for task in tasks:
                edges.append(GraphEdge(decision.id, task.id, RelationType.IMPACTS, (event.id,), 0.72))
        for left_index, left in enumerate(people):
            for right in people[left_index + 1:]:
                edges.append(GraphEdge(left.entity_id, right.entity_id, RelationType.COLLABORATES_WITH, (event.id,), 0.65))
                edges.append(GraphEdge(right.entity_id, left.entity_id, RelationType.COLLABORATES_WITH, (event.id,), 0.65))

        if self._correction.search(event.content):
            for node in derived:
                node.attributes["correction_evidence"] = True
        return nodes, edges


class KnowledgeGraphBuilder:
    """Build a separate evidence graph and temporal/entity connections."""

    def __init__(
        self,
        entity_resolver: EntityResolver | None = None,
        relationship_extractor: RelationshipExtractor | None = None,
    ) -> None:
        self.entity_resolver = entity_resolver or EntityResolver()
        self.relationship_extractor = relationship_extractor or RelationshipExtractor()

    def build(self, events: list[Event]) -> EvidenceGraph:
        graph = EvidenceGraph()
        events_by_entity: dict[str, list[Event]] = defaultdict(list)
        for event in events:
            mentions = self.entity_resolver.extract(event.content)
            nodes, edges = self.relationship_extractor.extract(event, mentions)
            for node in nodes:
                graph.add_node(node)
            for edge in edges:
                graph.add_edge(edge)
            for mention in mentions:
                events_by_entity[mention.entity_id].append(event)

        for entity_id, related_events in events_by_entity.items():
            ordered = sorted(related_events, key=lambda item: (item.timestamp, item.id))
            for earlier, later in zip(ordered, ordered[1:], strict=False):
                graph.add_edge(
                    GraphEdge(
                        f"event:{earlier.id}",
                        f"event:{later.id}",
                        RelationType.TEMPORALLY_ADJACENT,
                        (earlier.id, later.id),
                        0.72,
                        {"via_entity": entity_id},
                    )
                )

        ordered_events = sorted(events, key=lambda item: (item.timestamp, item.id))
        for position, event in enumerate(ordered_events):
            lowered = event.content.lower()
            is_correction = bool(RelationshipExtractor._correction.search(event.content))
            is_terminal = event.signals.is_completion or event.signals.is_cancellation
            if not is_correction and not is_terminal:
                continue
            terms = set(tokenize(event.content, remove_stopwords=True))
            candidates: list[tuple[int, Event]] = []
            for prior in ordered_events[:position]:
                common = terms & set(tokenize(prior.content, remove_stopwords=True))
                if len(common) >= 2:
                    candidates.append((len(common), prior))
            if not candidates:
                continue
            _, prior = max(candidates, key=lambda item: (item[0], item[1].timestamp))
            relation = RelationType.SUPERSEDES if is_correction else RelationType.COMPLETES
            target_id = f"event:{prior.id}"
            if is_terminal and graph.get(f"task:{prior.id}"):
                target_id = f"task:{prior.id}"
            graph.add_edge(
                GraphEdge(
                    f"event:{event.id}",
                    target_id,
                    relation,
                    (prior.id, event.id),
                    min(0.95, 0.62 + 0.05 * len(terms & set(tokenize(prior.content, remove_stopwords=True)))),
                )
            )
        return graph
