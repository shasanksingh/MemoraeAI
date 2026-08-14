export const overview = {
  priorities: 6,
  risks: 4,
  commitments: 31,
  projects: 27,
  graphNodes: 363,
  quality: 82,
};

export const priorities = [
  { title: "Finish the UIE proposal", meta: "Due today - Nina review at 14:30 IST", level: "critical" },
  { title: "Confirm external-safe diagrams", meta: "Due today - data-room access is waiting", level: "high" },
  { title: "Send Southridge redlines", meta: "Due tomorrow - clause 8 is approved", level: "high" },
  { title: "Close staging prevention notes", meta: "Past-due note from this morning", level: "medium" },
];

export const projects = [
  { name: "Unified Intelligence Engine", health: 72, risks: 3, activity: "8m ago" },
  { name: "Southridge SOW", health: 61, risks: 2, activity: "45m ago" },
  { name: "Admin Export", health: 84, risks: 1, activity: "tomorrow" },
];

export const timeline = [
  { time: "08:30", type: "Decision", title: "UIE deadline corrected to today at 15:00 IST" },
  { time: "09:10", type: "Risk", title: "External-safe diagrams still block data-room access" },
  { time: "10:45", type: "Meeting", title: "Proposal review moved to 14:30 IST" },
  { time: "12:20", type: "Commitment", title: "Southridge redlines promised by Aug 14" },
];

export const trendData = [
  { day: "Mon", completed: 8, created: 11, focus: 74 },
  { day: "Tue", completed: 13, created: 10, focus: 82 },
  { day: "Wed", completed: 9, created: 14, focus: 61 },
  { day: "Thu", completed: 15, created: 12, focus: 87 },
  { day: "Fri", completed: 11, created: 9, focus: 79 },
  { day: "Sat", completed: 5, created: 4, focus: 68 },
  { day: "Sun", completed: 7, created: 6, focus: 72 },
];
