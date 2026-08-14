"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  AudioLines,
  BrainCircuit,
  CalendarRange,
  FileSearch,
  FolderKanban,
  History,
  Network,
  Search,
  ShieldAlert,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useIntelligenceStore } from "@/store/intelligence";

const commands = [
  { label: "Search Memory", href: "/workspace", icon: Search, hint: "Ask across all evidence" },
  { label: "Analyze Meeting", href: "/workspace?mode=meeting", icon: CalendarRange, hint: "Extract decisions and follow-ups" },
  { label: "Find Decisions", href: "/memory", icon: BrainCircuit, hint: "Browse decision memory" },
  { label: "Search Graph", href: "/graph", icon: Network, hint: "Traverse people, projects, risks" },
  { label: "Generate Report", href: "/workspace?prompt=weekly-report", icon: FileSearch, hint: "Build an evidence-backed report" },
  { label: "Show Timeline", href: "/timeline", icon: History, hint: "Reconstruct what changed" },
  { label: "Create Task", href: "/workspace?mode=project", icon: FolderKanban, hint: "Draft a task from evidence" },
  { label: "Voice Query", href: "/workspace?mode=voice", icon: AudioLines, hint: "Dictate or upload audio" },
  { label: "Upload Evidence", href: "/workspace?upload=true", icon: Upload, hint: "PDF, DOCX, TXT, audio, video" },
  { label: "Show Risks", href: "/projects", icon: ShieldAlert, hint: "Risk and blocker view" },
];

export function CommandPalette() {
  const open = useIntelligenceStore((state) => state.commandOpen);
  const setOpen = useIntelligenceStore((state) => state.setCommandOpen);
  const history = useIntelligenceStore((state) => state.promptHistory);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const normalized = query.toLowerCase().trim();
    if (!normalized) return commands;
    return commands.filter((item) => `${item.label} ${item.hint}`.toLowerCase().includes(normalized));
  }, [query]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/55 p-4 backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={() => setOpen(false)}
        >
          <motion.div
            className="mx-auto mt-20 max-w-2xl overflow-hidden rounded-3xl border border-white/10 bg-[#0b0d14]/95 shadow-2xl"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-white/[.07] px-4 py-3">
              <Sparkles className="size-4 text-violet-300" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search commands, memories, projects, tasks..."
                className="h-10 flex-1 bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
              />
              <button onClick={() => setOpen(false)} className="rounded-lg p-2 text-zinc-500 hover:bg-white/5 hover:text-zinc-200">
                <X className="size-4" />
              </button>
            </div>
            <div className="grid gap-2 p-3">
              {filtered.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="group flex items-center gap-3 rounded-2xl px-3 py-3 transition hover:bg-white/[.055]"
                >
                  <span className="grid size-9 place-items-center rounded-xl border border-white/10 bg-white/[.04]">
                    <item.icon className="size-4 text-violet-300" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm text-zinc-200">{item.label}</span>
                    <span className="block text-xs text-zinc-600">{item.hint}</span>
                  </span>
                  <span className="ml-auto text-xs text-zinc-700 group-hover:text-zinc-400">Enter</span>
                </Link>
              ))}
            </div>
            {history.length > 0 && (
              <div className="border-t border-white/[.07] px-4 py-3">
                <p className="mb-2 text-[10px] uppercase tracking-[.2em] text-zinc-600">Recent prompts</p>
                <div className="flex flex-wrap gap-2">
                  {history.slice(0, 5).map((item) => (
                    <span key={item.id} className="rounded-full border border-white/10 bg-white/[.03] px-3 py-1 text-xs text-zinc-500">
                      {item.prompt}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
