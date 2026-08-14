"""Durable project-state facts derived from episodic and commitment memories."""

from __future__ import annotations

import hashlib

from app.memory.commitment import CommitmentMemory
from app.memory.models import Project, SemanticFact
from app.memory.project import ProjectMemory
from app.utils.time import human_delta


class SemanticMemory:
    """Create concise, evidence-linked facts for each discovered project."""

    def __init__(self, projects: ProjectMemory, commitments: CommitmentMemory) -> None:
        self._facts = self._derive(projects, commitments)

    @staticmethod
    def _fact(project: Project, statement: str, evidence: list[str], confidence: float) -> SemanticFact:
        digest = hashlib.sha1(f"{project.id}|{statement}".encode()).hexdigest()[:12]
        return SemanticFact(
            id=f"fact-{digest}",
            project_id=project.id,
            statement=statement,
            evidence_ids=evidence,
            valid_at=project.last_updated,
            confidence=confidence,
        )

    def _derive(self, projects: ProjectMemory, commitments: CommitmentMemory) -> list[SemanticFact]:
        facts: list[SemanticFact] = []
        open_items = commitments.open()
        for project in projects.all():
            facts.append(
                self._fact(
                    project,
                    f"{project.name} is an active topic supported by {len(project.event_ids)} event(s).",
                    project.event_ids,
                    min(0.95, 0.55 + 0.05 * len(project.event_ids)),
                )
            )
            related = [item for item in open_items if set(item.evidence_ids) & set(project.event_ids)]
            for item in sorted(related, key=lambda value: -value.risk_score)[:3]:
                timing = human_delta(item.deadline_at, commitments.as_of)
                statement = f"Open action: {item.title} ({timing})."
                if item.waiting_on:
                    statement += f" Waiting on {item.waiting_on}."
                facts.append(self._fact(project, statement, item.evidence_ids, 0.86))
        return facts

    def all(self) -> list[SemanticFact]:
        return list(self._facts)

    def for_project(self, project_id: str) -> list[SemanticFact]:
        return [fact for fact in self._facts if fact.project_id == project_id]
