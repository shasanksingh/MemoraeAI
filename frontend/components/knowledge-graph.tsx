"use client";

import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const nodes: Node[] = [
  { id: "uie", position: { x: 340, y: 180 }, data: { label: "UIE Project" }, style: { background: "#8b5cf6", color: "white", border: 0, borderRadius: 14, padding: 12 } },
  { id: "proposal", position: { x: 80, y: 70 }, data: { label: "Proposal v3" }, style: { background: "#171a25", color: "#e4e4e7", border: "1px solid #ffffff16", borderRadius: 12 } },
  { id: "nina", position: { x: 620, y: 50 }, data: { label: "Nina" }, style: { background: "#171a25", color: "#e4e4e7", border: "1px solid #ffffff16", borderRadius: 20 } },
  { id: "diagram", position: { x: 670, y: 290 }, data: { label: "External-safe diagrams" }, style: { background: "#171a25", color: "#e4e4e7", border: "1px solid #fb718544", borderRadius: 12 } },
  { id: "dataroom", position: { x: 390, y: 390 }, data: { label: "Data-room access" }, style: { background: "#171a25", color: "#e4e4e7", border: "1px solid #ffffff16", borderRadius: 12 } },
  { id: "decision", position: { x: 40, y: 300 }, data: { label: "Deadline correction" }, style: { background: "#171a25", color: "#e4e4e7", border: "1px solid #22d3ee44", borderRadius: 12 } },
];

const edges: Edge[] = [
  { id: "e1", source: "proposal", target: "uie", label: "belongs to", animated: true, style: { stroke: "#8b5cf6" } },
  { id: "e2", source: "nina", target: "uie", label: "reviews", style: { stroke: "#52525b" } },
  { id: "e3", source: "dataroom", target: "diagram", label: "blocked by", animated: true, style: { stroke: "#fb7185" } },
  { id: "e4", source: "diagram", target: "uie", label: "belongs to", style: { stroke: "#52525b" } },
  { id: "e5", source: "decision", target: "proposal", label: "impacts", style: { stroke: "#22d3ee" } },
];

export function KnowledgeGraph() {
  return <div className="glass h-[680px] overflow-hidden rounded-2xl"><ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark"><Background color="#ffffff14" gap={28} /><MiniMap nodeColor="#8b5cf6" maskColor="#07080dcc" /><Controls /></ReactFlow></div>;
}
