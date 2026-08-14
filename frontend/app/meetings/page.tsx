import { PageHeading } from "@/components/page-heading";
import { WorkspaceList } from "@/components/workspace-list";

const items = [
  { type: "Today · 14:30", title: "UIE proposal review with Nina", meta: "3 decisions expected · 2 open risks · brief ready" },
  { type: "Tomorrow · 10:00", title: "Candidate calibration", meta: "Blocked by scoring rubric · 4 participants" },
  { type: "Completed", title: "Admin export product review", meta: "5 action items · 2 decisions · transcript processed" },
];
export default function MeetingsPage() { return <><PageHeading eyebrow="Conversations" title="Meeting Intelligence" description="Prepare with context, capture decisions, and track every action after the room goes quiet." /><WorkspaceList items={items} /></>; }
