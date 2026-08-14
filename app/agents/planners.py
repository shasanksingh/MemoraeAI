"""Deterministic agentic planners that propose but never silently execute work."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.graph.evidence import EvidenceGraph
from app.graph.models import GraphNode, NodeType, RelationType
from app.utils.text import tokenize


@dataclass(frozen=True, slots=True)
class PlanStep:
    id: str
    title: str
    kind: str
    depends_on: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    priority: float
    status: str = "proposed"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "depends_on": list(self.depends_on),
            "evidence_ids": list(self.evidence_ids),
            "priority": round(self.priority, 4),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    id: str
    goal: str
    steps: tuple[PlanStep, ...]
    risks: tuple[str, ...]
    evidence_coverage: float
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "risks": list(self.risks),
            "evidence_coverage": round(self.evidence_coverage, 4),
            "rationale": list(self.rationale),
        }


class TaskPlanner:
    """Order evidence-backed tasks using graph dependencies and task attributes."""

    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def _priority(self, node: GraphNode) -> float:
        return (
            0.40 * float(node.attributes.get("urgency", 0.0))
            + 0.35 * float(node.attributes.get("risk", 0.0))
            + 0.25 * float(node.attributes.get("importance", 0.0))
        )

    def plan(self, task_nodes: list[GraphNode] | None = None, limit: int = 20) -> tuple[PlanStep, ...]:
        tasks = task_nodes or self.graph.nodes(NodeType.TASK)
        steps: list[PlanStep] = []
        for task in tasks:
            dependencies = tuple(
                neighbor.id
                for edge, neighbor in self.graph.adjacent(task.id, direction="out")
                if edge.relation in {RelationType.DEPENDS_ON, RelationType.BLOCKED_BY}
            )
            steps.append(
                PlanStep(
                    id=f"step:{task.id}",
                    title=task.label,
                    kind="task",
                    depends_on=dependencies,
                    evidence_ids=tuple(sorted(task.evidence_ids)),
                    priority=self._priority(task),
                )
            )
        return tuple(sorted(steps, key=lambda item: (-item.priority, item.title))[:limit])


class GoalPlanner:
    """Find task and decision evidence connected to an explicit or query-time goal."""

    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def related_nodes(self, goal: str) -> list[GraphNode]:
        seeds = {node.id for node in self.graph.find_entities(goal)}
        query_terms = set(tokenize(goal, remove_stopwords=True))
        seeds.update(
            node.id for node in self.graph.nodes(NodeType.GOAL)
            if query_terms & set(tokenize(node.label, remove_stopwords=True))
        )
        reached, _ = self.graph.expand(seeds, max_hops=3, max_nodes=250)
        return [
            node for node_id in reached
            if (node := self.graph.get(node_id)) and node.node_type in {NodeType.TASK, NodeType.DECISION, NodeType.RISK}
        ]


class EvidencePlanner:
    """Explain what evidence is still needed before a plan is reliable."""

    def gaps(self, goal: str, nodes: list[GraphNode]) -> tuple[str, ...]:
        kinds = {node.node_type for node in nodes}
        gaps: list[str] = []
        if NodeType.TASK not in kinds:
            gaps.append("No executable task evidence is connected to this goal.")
        if not any(node.evidence_ids for node in nodes):
            gaps.append("No raw source evidence supports the proposed workflow.")
        if NodeType.RISK not in kinds:
            gaps.append("No explicit risk evidence was found; risk coverage may be incomplete.")
        return tuple(gaps)


class ContextPlanner:
    """Allocate a bounded workflow context across tasks, risks, and decisions."""

    def select(self, nodes: list[GraphNode], limit: int = 30) -> list[GraphNode]:
        chosen: list[GraphNode] = []
        for node_type in (NodeType.TASK, NodeType.RISK, NodeType.DECISION, NodeType.GOAL):
            chosen.extend(node for node in nodes if node.node_type is node_type and node not in chosen)
        return chosen[:limit]


class WorkflowPlanner:
    """Compose goal, context, evidence, and task planning into an auditable proposal."""

    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph
        self.goal_planner = GoalPlanner(graph)
        self.context_planner = ContextPlanner()
        self.evidence_planner = EvidencePlanner()
        self.task_planner = TaskPlanner(graph)

    def plan(self, goal: str) -> WorkflowPlan:
        related = self.goal_planner.related_nodes(goal)
        context = self.context_planner.select(related)
        task_nodes = [node for node in context if node.node_type is NodeType.TASK]
        steps = self.task_planner.plan(task_nodes)
        risks = tuple(node.label for node in context if node.node_type is NodeType.RISK)
        supported = sum(bool(node.evidence_ids) for node in context)
        coverage = supported / max(1, len(context))
        gaps = self.evidence_planner.gaps(goal, context)
        digest = hashlib.sha1(goal.strip().lower().encode()).hexdigest()[:12]
        return WorkflowPlan(
            id=f"workflow:{digest}",
            goal=goal,
            steps=steps,
            risks=risks,
            evidence_coverage=coverage,
            rationale=(
                "Plan generated from graph-connected tasks, decisions, dependencies, and risks.",
                "All steps remain proposed until the user explicitly approves execution.",
                *gaps,
            ),
        )

