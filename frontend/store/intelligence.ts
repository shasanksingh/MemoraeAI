import { create } from "zustand";
import type { IntelligenceAnswer } from "@/lib/api";

export type WorkspaceTab = {
  id: string;
  title: string;
  mode: "research" | "meeting" | "memory" | "project" | "voice" | "graph";
};

type PromptRecord = {
  id: string;
  prompt: string;
  createdAt: string;
  answer?: IntelligenceAnswer;
};

type IntelligenceState = {
  commandOpen: boolean;
  selectedProject: string | null;
  tabs: WorkspaceTab[];
  activeTabId: string;
  promptHistory: PromptRecord[];
  setCommandOpen: (open: boolean) => void;
  selectProject: (project: string | null) => void;
  addTab: (tab: WorkspaceTab) => void;
  setActiveTab: (id: string) => void;
  addPromptRecord: (record: PromptRecord) => void;
};

const initialTabs: WorkspaceTab[] = [
  { id: "memory-search", title: "Memory Search", mode: "memory" },
  { id: "graphrag-research", title: "GraphRAG Research", mode: "research" },
  { id: "project-intel", title: "Project Intelligence", mode: "project" },
];

export const useIntelligenceStore = create<IntelligenceState>((set) => ({
  commandOpen: false,
  selectedProject: null,
  tabs: initialTabs,
  activeTabId: initialTabs[0].id,
  promptHistory: [],
  setCommandOpen: (commandOpen) => set({ commandOpen }),
  selectProject: (selectedProject) => set({ selectedProject }),
  addTab: (tab) =>
    set((state) => ({
      tabs: state.tabs.some((item) => item.id === tab.id) ? state.tabs : [...state.tabs, tab],
      activeTabId: tab.id,
    })),
  setActiveTab: (activeTabId) => set({ activeTabId }),
  addPromptRecord: (record) =>
    set((state) => ({
      promptHistory: [record, ...state.promptHistory].slice(0, 24),
    })),
}));
