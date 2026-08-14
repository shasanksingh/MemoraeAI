"""Knowledge graph construction, provenance, and persistence."""

from app.graph.models import NodeType, RelationType


def test_graph_nodes_have_raw_evidence(system) -> None:
    assert system.graph is not None
    derived = [node for node in system.graph.nodes() if node.node_type is not NodeType.EVENT]
    assert derived
    assert all(node.evidence_ids for node in derived)


def test_graph_contains_dependencies_and_temporal_edges(system) -> None:
    assert system.graph is not None
    relations = {edge.relation for edge in system.graph.edges()}
    assert RelationType.BLOCKED_BY in relations
    assert RelationType.TEMPORALLY_ADJACENT in relations
    assert RelationType.COLLABORATES_WITH in relations
    assert RelationType.HAS_RISK in relations


def test_extended_memories_are_materialized(system) -> None:
    assert system.relationships and system.relationships.all()
    assert system.interactions and system.interactions.all()
    assert system.temporal_events and system.temporal_events.all()
    assert system.activities and system.activities.all()
    assert system.decisions and system.decisions.all()
    assert system.meetings and system.meetings.all()


def test_workflow_planner_returns_evidence_backed_proposal(system) -> None:
    plan = system.plan_goal("Complete the UIE proposal")
    assert plan["id"].startswith("workflow:")
    assert plan["steps"]
    assert all(step["status"] == "proposed" for step in plan["steps"])
