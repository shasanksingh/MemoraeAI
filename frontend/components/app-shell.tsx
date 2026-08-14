"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Activity,
  AudioLines,
  BrainCircuit,
  CalendarRange,
  ChartNoAxesCombined,
  ChevronRight,
  CircleUserRound,
  Command,
  FolderKanban,
  LayoutDashboard,
  Menu,
  MessageSquareText,
  Network,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { useIntelligenceStore } from "@/store/intelligence";
import { CommandPalette } from "@/components/command-palette";

const navigation = [
  { href: "/", label: "Intelligence", icon: LayoutDashboard },
  { href: "/workspace", label: "AI Workspace", icon: Sparkles },
  { href: "/memory", label: "Memory Explorer", icon: BrainCircuit },
  { href: "/graph", label: "Knowledge Graph", icon: Network },
  { href: "/timeline", label: "Timeline", icon: CalendarRange },
  { href: "/voice", label: "Voice Intelligence", icon: AudioLines },
  { href: "/meetings", label: "Meetings", icon: MessageSquareText },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/analytics", label: "Analytics", icon: ChartNoAxesCombined },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const setCommandOpen = useIntelligenceStore((state) => state.setCommandOpen);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setCommandOpen]);

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] border-r border-white/[.07] bg-[#090b11]/90 px-3 py-4 backdrop-blur-2xl lg:block">
        <Link href="/" className="mb-7 flex items-center gap-3 px-3">
          <Image src="/brand/memorae-mark.svg" alt="" width={36} height={36} className="drop-shadow-[0_0_24px_rgba(34,211,238,.24)]" priority />
          <div>
            <p className="text-sm font-semibold tracking-wide">MEMORAE</p>
            <p className="text-[10px] uppercase tracking-[.18em] text-zinc-500">Intelligence OS</p>
          </div>
        </Link>
        <nav className="space-y-1">
          {navigation.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group relative flex h-10 items-center gap-3 rounded-xl px-3 text-[13px] transition",
                  active ? "bg-white/[.075] text-white" : "text-zinc-500 hover:bg-white/[.04] hover:text-zinc-200",
                )}
              >
                {active && <motion.span layoutId="active-nav" className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-violet-400" />}
                <item.icon className="size-4" />
                <span>{item.label}</span>
                {active && <ChevronRight className="ml-auto size-3.5 text-zinc-600" />}
              </Link>
            );
          })}
        </nav>
        <div className="absolute inset-x-3 bottom-4 rounded-2xl border border-violet-400/10 bg-violet-400/[.045] p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs text-violet-200">
            <Activity className="size-3.5" /> Memory is healthy
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-white/5">
            <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" />
          </div>
          <p className="mt-2 text-[10px] text-zinc-600">164 events - 363 graph nodes</p>
        </div>
      </aside>
      <div className="min-w-0 flex-1 lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-white/[.06] bg-[#07080d]/75 px-5 backdrop-blur-xl md:px-8">
          <Menu className="size-5 text-zinc-500 lg:hidden" />
          <button
            onClick={() => setCommandOpen(true)}
            className="flex h-9 max-w-md flex-1 items-center gap-2 rounded-xl border border-white/[.08] bg-white/[.035] px-3 text-left text-xs text-zinc-500 transition hover:bg-white/[.06]"
          >
            <Search className="size-3.5" />
            Ask anything across your memory...
            <span className="ml-auto flex items-center gap-1 rounded-md border border-white/10 px-1.5 py-0.5 text-[10px]">
              <Command className="size-2.5" />K
            </span>
          </button>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-xs text-zinc-500 sm:inline">Synced 2m ago</span>
            <CircleUserRound className="size-7 text-zinc-400" />
          </div>
        </header>
        <main className="subtle-grid min-h-[calc(100vh-4rem)] p-5 md:p-8">{children}</main>
      </div>
      <CommandPalette />
    </div>
  );
}
