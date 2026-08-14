"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Clock3, FolderKanban, Network, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { overview, priorities, projects, timeline } from "@/lib/data";

const metrics = [
  { label: "Open commitments", value: overview.commitments, hint: "6 need attention", icon: CheckCircle2, color: "text-violet-400" },
  { label: "Active risks", value: overview.risks, hint: "2 new today", icon: AlertTriangle, color: "text-rose-400" },
  { label: "Projects", value: overview.projects, hint: "3 updated today", icon: FolderKanban, color: "text-cyan-400" },
  { label: "Graph intelligence", value: overview.graphNodes, hint: "594 relationships", icon: Network, color: "text-emerald-400" },
];

export function Dashboard() {
  return (
    <div className="space-y-5">
      <section className="relative h-36 overflow-hidden rounded-2xl border border-white/[.07] bg-[#090b11] md:h-44">
        <Image
          src="/brand/memorae-intelligence-map.png"
          alt="Abstract memory graph visualization"
          fill
          priority
          sizes="(min-width: 1024px) calc(100vw - 312px), calc(100vw - 40px)"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#07080d]/80 via-[#07080d]/18 to-[#07080d]/32" />
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#07080d] to-transparent" />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric, index) => (
          <motion.div key={metric.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
            <Card className="p-4">
              <div className="flex items-start justify-between">
                <metric.icon className={`size-4 ${metric.color}`} />
                <ArrowUpRight className="size-3.5 text-zinc-700" />
              </div>
              <p className="mt-5 text-2xl font-semibold tracking-tight">{metric.value}</p>
              <p className="mt-1 text-xs text-zinc-500">{metric.label}</p>
              <p className="mt-3 text-[10px] text-zinc-600">{metric.hint}</p>
            </Card>
          </motion.div>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <Card>
          <CardHeader>
            <div>
              <p className="text-sm font-medium">Today's intelligence brief</p>
              <p className="mt-1 text-xs text-zinc-600">Evidence-backed priorities, not another notification feed.</p>
            </div>
            <Badge className="border-emerald-400/20 bg-emerald-400/5 text-emerald-300">
              <ShieldCheck className="mr-1 inline size-3" />82% context quality
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2">
            {priorities.map((item, index) => (
              <div key={item.title} className="group flex items-center gap-3 rounded-xl border border-transparent px-2 py-3 transition hover:border-white/[.06] hover:bg-white/[.025]">
                <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-white/[.04] text-[11px] text-zinc-500">{index + 1}</span>
                <div className="min-w-0">
                  <p className="truncate text-[13px] text-zinc-200">{item.title}</p>
                  <p className="mt-1 text-[11px] text-zinc-600">{item.meta}</p>
                </div>
                <span className={`ml-auto size-1.5 rounded-full ${item.level === "critical" ? "bg-rose-400" : item.level === "high" ? "bg-amber-400" : "bg-cyan-400"}`} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <p className="text-sm font-medium">Living timeline</p>
              <p className="mt-1 text-xs text-zinc-600">What changed and why it matters.</p>
            </div>
            <Clock3 className="size-4 text-zinc-600" />
          </CardHeader>
          <CardContent className="space-y-0">
            {timeline.map((item, index) => (
              <div key={item.title} className="relative flex gap-4 pb-5 last:pb-0">
                <div className="flex w-10 flex-col items-center">
                  <span className="text-[10px] text-zinc-600">{item.time}</span>
                  <span className="mt-2 size-2 rounded-full border-2 border-violet-400 bg-[#12151f]" />
                  {index < timeline.length - 1 && <span className="mt-1 h-full w-px bg-white/[.07]" />}
                </div>
                <div>
                  <Badge>{item.type}</Badge>
                  <p className="mt-2 text-xs leading-5 text-zinc-300">{item.title}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <div>
            <p className="text-sm font-medium">Project intelligence</p>
            <p className="mt-1 text-xs text-zinc-600">Health combines risks, blockers, commitments, and recent decisions.</p>
          </div>
          <button className="text-xs text-violet-400">Open workspace -&gt;</button>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {projects.map((project) => (
            <div key={project.name} className="rounded-xl border border-white/[.06] bg-black/10 p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-zinc-200">{project.name}</p>
                <span className="text-[10px] text-zinc-600">{project.activity}</span>
              </div>
              <div className="mt-5 flex items-end justify-between">
                <div>
                  <p className="text-2xl font-semibold">
                    {project.health}
                    <span className="text-xs text-zinc-600">%</span>
                  </p>
                  <p className="mt-1 text-[10px] text-zinc-600">health score</p>
                </div>
                <Badge className={project.risks > 2 ? "text-rose-300" : "text-amber-300"}>
                  {project.risks} risk{project.risks > 1 ? "s" : ""}
                </Badge>
              </div>
              <div className="mt-3 h-1 rounded-full bg-white/5">
                <div style={{ width: `${project.health}%` }} className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
