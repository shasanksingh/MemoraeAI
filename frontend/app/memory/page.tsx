import { PageHeading } from "@/components/page-heading";
import { WorkspaceList } from "@/components/workspace-list";

const items = [
  { type: "Decision", title: "Use $48.5k as the year-one licensing estimate", meta: "UIE - corrected 2h ago - 2 evidence items" },
  { type: "Commitment", title: "Send Southridge SOW redlines", meta: "Open - clause 8 is approved" },
  { type: "Meeting", title: "UIE proposal review with Nina", meta: "Today 14:30 IST - Northstar Meet" },
  { type: "Learning", title: "External reviewers need sanitized architecture diagrams", meta: "UIE - learned from data-room access blocker" },
  { type: "Preference", title: "Keep mornings clear for focused work", meta: "Observed across 3 calendar events" },
];

export default function MemoryPage() {
  return (
    <>
      <PageHeading
        eyebrow="Explore"
        title="Memory Explorer"
        description="Browse durable decisions, commitments, meetings, preferences, and learnings with their source evidence."
      />
      <WorkspaceList items={items} />
    </>
  );
}
