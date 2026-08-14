"""Composition root for the Memorae Personal Intelligence Platform."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import Settings
from app.agents.planners import WorkflowPlanner
from app.graph.extraction import KnowledgeGraphBuilder
from app.graph.store import KnowledgeGraphStore
from app.ingestion.loader import EventLoader
from app.memory.activity import ActivityMemory
from app.memory.commitment import CommitmentMemory
from app.memory.decision import DecisionMemory
from app.memory.episodic import EpisodicMemory
from app.memory.interaction import InteractionMemory
from app.memory.goal import GoalMemory
from app.memory.learning import LearningMemory
from app.memory.meeting import MeetingMemory
from app.memory.preference import PreferenceMemory
from app.memory.project import ProjectMemory
from app.memory.relationship import RelationshipMemory
from app.memory.semantic import SemanticMemory
from app.memory.store import SQLiteSnapshotStore
from app.memory.temporal_event import TemporalEventMemory
from app.reasoning.evidence_context import EvidenceContextAssembler
from app.reasoning.extraction import SignalExtractor
from app.reasoning.query_engine import QueryEngine
from app.retrieval.embeddings import Embedder, HashingEmbedder
from app.retrieval.expansion import EvidenceDiscoveryEngine
from app.retrieval.graphrag import GraphRAGRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.planner import RetrievalPlanner
from app.utils.time import isoformat

LOGGER = logging.getLogger(__name__)


class PersonalIntelligencePlatform:
    """Build and query an evidence-first personal intelligence snapshot."""

    def __init__(self, settings: Settings | None = None, embedder: Embedder | None = None) -> None:
        self.settings = settings or Settings()
        self.embedder = embedder or HashingEmbedder(self.settings.embedding_dimension)
        self.episodic: EpisodicMemory | None = None
        self.commitments: CommitmentMemory | None = None
        self.projects: ProjectMemory | None = None
        self.semantic: SemanticMemory | None = None
        self.relationships: RelationshipMemory | None = None
        self.preferences: PreferenceMemory | None = None
        self.interactions: InteractionMemory | None = None
        self.temporal_events: TemporalEventMemory | None = None
        self.activities: ActivityMemory | None = None
        self.decisions: DecisionMemory | None = None
        self.meetings: MeetingMemory | None = None
        self.goals: GoalMemory | None = None
        self.learnings: LearningMemory | None = None
        self.graph = None
        self.query_engine: QueryEngine | None = None
        self.future_events_excluded = 0
        self.ingestion_lineage = []
        self.data_quality = None
        self.workflow_planner: WorkflowPlanner | None = None

    @classmethod
    def from_json(
        cls,
        path: str | Path | None = None,
        settings: Settings | None = None,
        embedder: Embedder | None = None,
    ) -> "PersonalIntelligencePlatform":
        system = cls(settings=settings, embedder=embedder)
        system.ingest_json(path or Settings.default_data_path())
        return system

    def ingest_json(self, path: str | Path) -> None:
        extractor = SignalExtractor(self.settings.as_of)
        loader = EventLoader(extractor, self.settings.as_of)
        events = loader.load_json(path)
        self.future_events_excluded = loader.excluded_future_count
        self.ingestion_lineage = loader.lineage
        self.data_quality = loader.quality_report
        self.episodic = EpisodicMemory(events)
        self.commitments = CommitmentMemory(events, self.settings.as_of)
        self.projects = ProjectMemory(events, self.embedder, threshold=0.18)
        self.semantic = SemanticMemory(self.projects, self.commitments)
        self.graph = KnowledgeGraphBuilder().build(events)
        self.relationships = RelationshipMemory(self.graph)
        self.preferences = PreferenceMemory(self.graph)
        self.interactions = InteractionMemory(events, self.graph)
        self.temporal_events = TemporalEventMemory(events)
        self.activities = ActivityMemory(self.graph)
        self.decisions = DecisionMemory(self.graph)
        self.meetings = MeetingMemory(self.graph)
        self.goals = GoalMemory(self.graph)
        self.learnings = LearningMemory(self.graph)
        self.workflow_planner = WorkflowPlanner(self.graph)

        recall = HybridRetriever(
            events,
            self.embedder,
            self.settings.as_of,
            candidate_pool=self.settings.candidate_pool_size,
        )
        planner = RetrievalPlanner(
            broad_limit=self.settings.candidate_pool_size,
            final_limit=self.settings.retrieval_k,
            max_rounds=self.settings.max_expansion_rounds,
            max_hops=self.settings.graph_max_hops,
        )
        discovery = EvidenceDiscoveryEngine(
            self.graph,
            events,
            temporal_neighbors=self.settings.temporal_neighbor_count,
            max_events=self.settings.max_expanded_events,
        )
        graph_retriever = GraphRAGRetriever(self.graph, recall, planner, discovery)
        context_builder = EvidenceContextAssembler(
            self.graph,
            token_budget=self.settings.context_token_budget,
            near_duplicate_threshold=self.settings.near_duplicate_threshold,
        )
        self.query_engine = QueryEngine(
            graph_retriever,
            self.graph,
            context_builder,
            self.settings.as_of,
            future_events_excluded=self.future_events_excluded,
        )
        LOGGER.info("Built %d-event snapshot with %d graph nodes", len(events), len(self.graph.nodes()))

    def answer_query(self, query: str) -> dict[str, Any]:
        if self.query_engine is None:
            raise RuntimeError("No snapshot loaded; call ingest_json first")
        return self.query_engine.answer_query(query).to_dict()

    def plan_goal(self, goal: str) -> dict[str, object]:
        """Return an evidence-backed proposed workflow without executing actions."""

        if self.workflow_planner is None:
            raise RuntimeError("No snapshot loaded; call ingest_json first")
        if not goal.strip():
            raise ValueError("goal cannot be empty")
        return self.workflow_planner.plan(goal).to_dict()

    def snapshot(self) -> dict[str, Any]:
        if not all((self.episodic, self.commitments, self.projects, self.semantic, self.graph)):
            raise RuntimeError("No snapshot loaded; call ingest_json first")
        assert self.episodic and self.commitments and self.projects and self.semantic and self.graph
        return {
            "as_of": isoformat(self.settings.as_of),
            "retrieval_backend": self.embedder.name,
            "storage_root": str(self.settings.storage.root),
            "future_events_excluded": self.future_events_excluded,
            "data_quality": {
                "score": self.data_quality.quality_score if self.data_quality else 1.0,
                "accepted": self.data_quality.accepted if self.data_quality else 0,
                "rejected": self.data_quality.rejected if self.data_quality else 0,
                "duplicates": self.data_quality.duplicates if self.data_quality else 0,
                "lineage_records": len(self.ingestion_lineage),
            },
            "counts": {
                "episodes": len(self.episodic),
                "commitments": len(self.commitments.all()),
                "open_commitments": len(self.commitments.open()),
                "projects": len(self.projects.all()),
                "semantic_facts": len(self.semantic.all()),
                "relationships": len(self.relationships.all()) if self.relationships else 0,
                "preferences": len(self.preferences.all()) if self.preferences else 0,
                "interactions": len(self.interactions.all()) if self.interactions else 0,
                "activities": len(self.activities.all()) if self.activities else 0,
                "decisions": len(self.decisions.all()) if self.decisions else 0,
                "meetings": len(self.meetings.all()) if self.meetings else 0,
                "goals": len(self.goals.all()) if self.goals else 0,
                "learnings": len(self.learnings.all()) if self.learnings else 0,
                "graph_nodes": len(self.graph.nodes()),
                "graph_edges": len(self.graph.edges()),
            },
            "commitments": [item.to_dict() for item in self.commitments.all()],
            "projects": [project.to_dict() for project in self.projects.all()],
            "semantic_facts": [fact.to_dict() for fact in self.semantic.all()],
        }

    def persist(self, path: str | Path) -> dict[str, int]:
        if not all((self.episodic, self.commitments, self.projects, self.semantic, self.graph)):
            raise RuntimeError("No snapshot loaded; call ingest_json first")
        assert self.episodic and self.commitments and self.projects and self.semantic and self.graph
        path = Path(path)
        store = SQLiteSnapshotStore(path)
        store.save(
            as_of=isoformat(self.settings.as_of) or "",
            events=self.episodic.all(),
            commitments=self.commitments.all(),
            projects=self.projects.all(),
            facts=self.semantic.all(),
            lineage=self.ingestion_lineage,
        )
        counts = store.counts()
        graph_path = path.with_name(f"{path.stem}-graph{path.suffix or '.sqlite3'}")
        counts.update(KnowledgeGraphStore(graph_path).save(self.graph))
        return counts


# Backward-compatible public name for existing integrations.
MemoryIntelligenceSystem = PersonalIntelligencePlatform
