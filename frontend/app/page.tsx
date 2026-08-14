import { Dashboard } from "@/components/dashboard";
import { PageHeading } from "@/components/page-heading";
import { Sparkles } from "lucide-react";

export default function IntelligencePage() {
  return (
    <>
      <PageHeading
        eyebrow="Thursday - 13 August"
        title="Welcome, Shashank."
        description="Your personal operating picture: priorities, risks, project movement, and the evidence behind them."
        action={
          <button className="glass flex items-center gap-2 rounded-xl px-4 py-2 text-xs text-zinc-300">
            <Sparkles className="size-3.5 text-violet-400" />
            Generate daily brief
          </button>
        }
      />
      <Dashboard />
    </>
  );
}
