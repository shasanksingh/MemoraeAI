"use client";

import { useMemo, useRef, useState } from "react";
import {
  AudioLines,
  Brain,
  CheckCircle2,
  Clock3,
  FileUp,
  GitBranch,
  Layers3,
  Link2,
  type LucideIcon,
  Loader2,
  Mic,
  Network,
  PanelRight,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { streamMemoryQuery, uploadFiles, type EvidenceContext, type IntelligenceAnswer, type StreamEvent } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useIntelligenceStore, type WorkspaceTab } from "@/store/intelligence";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

const suggestions = [
  "What should I focus on today?",
  "Summarize yesterday's meetings.",
  "Show every decision related to the UIE proposal.",
  "What commitments are at risk?",
  "Find all conversations with Rahul about GraphRAG.",
  "What changed this week?",
  "Generate a weekly intelligence report.",
  "Show blockers.",
];

const slashCommands = [
  { command: "/search-memory", label: "Search Memory", prompt: "Find all evidence related to " },
  { command: "/analyze-meeting", label: "Analyze Meeting", prompt: "Analyze the latest meeting and extract decisions, blockers, and follow-ups." },
  { command: "/find-decisions", label: "Find Decisions", prompt: "Show every decision related to " },
  { command: "/search-graph", label: "Search Graph", prompt: "Search the knowledge graph for relationships around " },
  { command: "/generate-report", label: "Generate Report", prompt: "Generate a weekly intelligence report." },
  { command: "/show-timeline", label: "Show Timeline", prompt: "Show a timeline of what changed this week." },
  { command: "/create-task", label: "Create Task", prompt: "Create a follow-up task from the current evidence: " },
  { command: "/voice-query", label: "Voice Query", prompt: "" },
];

const workspaceTemplates: WorkspaceTab[] = [
  { id: "meeting-analysis", title: "Meeting Analysis", mode: "meeting" },
  { id: "voice-analysis", title: "Voice Analysis", mode: "voice" },
  { id: "knowledge-graph", title: "Knowledge Graph", mode: "graph" },
];

function uniqueGraphNodes(answer?: IntelligenceAnswer) {
  const nodes = new Map<string, { id: string; type: string; label: string }>();
  answer?.selected_context?.forEach((item) => {
    item.evidence_graph?.nodes?.forEach((node) => nodes.set(node.id, node));
  });
  return Array.from(nodes.values()).slice(0, 18);
}

function evidenceTimeline(answer?: IntelligenceAnswer) {
  return [...(answer?.selected_context || [])]
    .sort((left, right) => left.timestamp.localeCompare(right.timestamp))
    .slice(0, 8);
}

function sourceCounts(context: EvidenceContext[]) {
  return context.reduce<Record<string, number>>((acc, item) => {
    acc[item.source] = (acc[item.source] || 0) + 1;
    return acc;
  }, {});
}

export function AICommandCenter() {
  const tabs = useIntelligenceStore((state) => state.tabs);
  const activeTabId = useIntelligenceStore((state) => state.activeTabId);
  const setActiveTab = useIntelligenceStore((state) => state.setActiveTab);
  const addTab = useIntelligenceStore((state) => state.addTab);
  const promptHistory = useIntelligenceStore((state) => state.promptHistory);
  const addPromptRecord = useIntelligenceStore((state) => state.addPromptRecord);

  const [prompt, setPrompt] = useState("");
  const [dataText, setDataText] = useState("");
  const [showDataInput, setShowDataInput] = useState(false);
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [status, setStatus] = useState<Array<{ label: string; detail: string }>>([]);
  const [answer, setAnswer] = useState<IntelligenceAnswer | null>(null);
  const [storageRoot, setStorageRoot] = useState<string | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const activeTab = tabs.find((tab) => tab.id === activeTabId) || tabs[0];
  const graphNodes = useMemo(() => uniqueGraphNodes(answer || undefined), [answer]);
  const timeline = useMemo(() => evidenceTimeline(answer || undefined), [answer]);
  const sources = useMemo(() => sourceCounts(answer?.selected_context || []), [answer]);
  const claims = answer?.reasoning.supported_claims || [];
  const tasks = claims.filter((claim) => claim.type === "task").slice(0, 6);
  const risks = claims.filter((claim) => ["risk", "dependency", "deadline"].includes(claim.type)).slice(0, 6);
  const confidence = Math.round((answer?.reasoning.context_quality.score || 0) * 100);

  async function runPrompt(nextPrompt = prompt) {
    const query = nextPrompt.trim();
    if (!query || isRunning) return;
    setPrompt(query);
    setIsRunning(true);
    setError(null);
    setAnswer(null);
    setStreamedAnswer("");
    setStatus([{ label: "Starting", detail: "Opening the evidence-first retrieval pipeline." }]);
    try {
      await streamMemoryQuery(query, showDataInput && dataText.trim() ? dataText : undefined, (event: StreamEvent) => {
        if (event.type === "status") setStatus((items) => [...items, { label: event.label, detail: event.detail }]);
        if (event.type === "token") setStreamedAnswer((current) => current + event.text);
        if (event.type === "error") setError(`${event.error}${event.details ? ` ${event.details}` : ""}`);
        if (event.type === "final") {
          setAnswer(event.result.answer);
          setStorageRoot(event.result.storageRoot);
          setUploadedPath(event.result.uploadedDataPath || null);
          addPromptRecord({
            id: crypto.randomUUID(),
            prompt: query,
            createdAt: new Date().toISOString(),
            answer: event.result.answer,
          });
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setIsRunning(false);
    }
  }

  async function onFiles(files: FileList | File[]) {
    const fileArray = Array.from(files);
    if (!fileArray.length) return;
    setUploadStatus("Uploading evidence into project storage...");
    setError(null);
    try {
      const result = await uploadFiles(fileArray);
      setStorageRoot(result.storageRoot);
      setUploadStatus(`${result.files.length} file(s) queued for ingestion. Manifest: ${result.manifestPath}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setUploadStatus(null);
    }
  }

  function startVoiceInput() {
    const browser = window as Window & {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Recognition = browser.SpeechRecognition || browser.webkitSpeechRecognition;
    if (!Recognition) {
      setError("Browser speech recognition is not available. Upload audio and configure a hosted Speech API instead.");
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map((result) => result[0].transcript).join(" ");
      setPrompt((current) => `${current} ${transcript}`.trim());
    };
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => {
      setIsListening(false);
      setError("Voice capture failed. Try again or upload an audio file.");
    };
    setIsListening(true);
    recognition.start();
  }

  function applySlashCommand(command: string) {
    const item = slashCommands.find((entry) => entry.command === command);
    if (!item) return;
    setPrompt(item.prompt);
    if (command === "/voice-query") startVoiceInput();
  }

  const showSlash = prompt.trim().startsWith("/");

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-5">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(139,92,246,.18),rgba(34,211,238,.08),rgba(255,255,255,.02))] p-5 shadow-2xl md:p-7">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(255,255,255,.12),transparent_24rem)]" />
        <div className="relative flex flex-col gap-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div>
              <Badge className="border-violet-400/20 bg-violet-400/10 text-violet-200">AI Command Center</Badge>
              <h1 className="mt-4 text-3xl font-semibold tracking-[-.04em] text-white md:text-5xl">
                Ask, investigate, upload, and act from one workspace.
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">
                A full-screen operating layer over memory, evidence, knowledge graph, timeline, projects, meetings, and tasks.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <p className="text-xl font-semibold">{confidence || 82}%</p>
                <p className="text-[10px] uppercase tracking-[.18em] text-zinc-500">Confidence</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <p className="text-xl font-semibold">{answer?.selected_context.length || 0}</p>
                <p className="text-[10px] uppercase tracking-[.18em] text-zinc-500">Evidence</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <p className="text-xl font-semibold">{graphNodes.length || 0}</p>
                <p className="text-[10px] uppercase tracking-[.18em] text-zinc-500">Graph nodes</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs transition",
                  activeTab.id === tab.id ? "border-violet-400/40 bg-violet-400/15 text-violet-100" : "border-white/10 bg-black/15 text-zinc-500 hover:text-zinc-200",
                )}
              >
                {tab.title}
              </button>
            ))}
            <div className="flex gap-1">
              {workspaceTemplates.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => addTab(tab)}
                  className="rounded-full border border-white/10 bg-white/[.03] px-2.5 py-1.5 text-xs text-zinc-500 hover:text-zinc-200"
                  title={`Open ${tab.title}`}
                >
                  <Plus className="inline size-3" /> {tab.title}
                </button>
              ))}
            </div>
          </div>

          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              void onFiles(event.dataTransfer.files);
            }}
            className="rounded-3xl border border-white/10 bg-[#080a10]/80 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,.05)] backdrop-blur-xl"
          >
            <div className="relative">
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void runPrompt();
                }}
                placeholder='Ask: "What commitments are at risk?" or type / for commands'
                className="min-h-32 w-full resize-none rounded-2xl border border-white/[.06] bg-black/30 p-4 pr-14 text-sm leading-6 text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-violet-400/30"
              />
              <button
                onClick={() => void runPrompt()}
                disabled={isRunning || !prompt.trim()}
                className="absolute bottom-3 right-3 grid size-10 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isRunning ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              </button>
            </div>

            {showSlash && (
              <div className="mt-2 grid gap-2 rounded-2xl border border-white/10 bg-black/35 p-2 md:grid-cols-4">
                {slashCommands.map((item) => (
                  <button
                    key={item.command}
                    onClick={() => applySlashCommand(item.command)}
                    className="rounded-xl px-3 py-2 text-left text-xs text-zinc-400 transition hover:bg-white/[.06] hover:text-zinc-100"
                  >
                    <span className="block text-violet-300">{item.command}</span>
                    {item.label}
                  </button>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button onClick={startVoiceInput} className={cn("rounded-xl border px-3 py-2 text-xs", isListening ? "border-rose-400/40 bg-rose-400/10 text-rose-200" : "border-white/10 bg-white/[.03] text-zinc-400 hover:text-zinc-100")}>
                <Mic className="mr-1 inline size-3.5" /> {isListening ? "Listening..." : "Voice input"}
              </button>
              <button onClick={() => fileInputRef.current?.click()} className="rounded-xl border border-white/10 bg-white/[.03] px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100">
                <FileUp className="mr-1 inline size-3.5" /> Upload files
              </button>
              <button onClick={() => setShowDataInput((value) => !value)} className="rounded-xl border border-white/10 bg-white/[.03] px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100">
                <Layers3 className="mr-1 inline size-3.5" /> Paste event JSON
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.markdown,audio/*,video/*,image/*,application/json"
                onChange={(event) => {
                  if (event.target.files) void onFiles(event.target.files);
                }}
              />
              <span className="ml-auto text-[11px] text-zinc-600">Ctrl + Enter to run - Ctrl + K for palette</span>
            </div>
            {showDataInput && (
              <textarea
                value={dataText}
                onChange={(event) => setDataText(event.target.value)}
                placeholder="Paste a JSON array of event records to run the backend against custom frontend-provided data."
                className="mt-3 min-h-32 w-full resize-y rounded-2xl border border-white/[.06] bg-black/30 p-4 font-mono text-xs leading-5 text-zinc-300 outline-none placeholder:text-zinc-700 focus:border-cyan-400/30"
              />
            )}
            {uploadStatus && <p className="mt-3 text-xs text-emerald-300">{uploadStatus}</p>}
            {uploadedPath && <p className="mt-2 text-xs text-zinc-600">Custom data used: {uploadedPath}</p>}
            {storageRoot && <p className="mt-2 text-xs text-zinc-600">Project storage: {storageRoot}</p>}
            {error && <p className="mt-3 rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
          </div>

          <div className="flex flex-wrap gap-2">
            {suggestions.map((item) => (
              <button key={item} onClick={() => void runPrompt(item)} className="rounded-full border border-white/10 bg-white/[.03] px-3 py-1.5 text-xs text-zinc-500 transition hover:border-violet-400/30 hover:text-zinc-100">
                {item}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <div>
                <p className="text-sm font-medium">Answer stream</p>
                <p className="mt-1 text-xs text-zinc-600">The answer is built from retrieved evidence, not a blind chat response.</p>
              </div>
              <Badge className={answer?.reasoning.claim_validation.valid ? "text-emerald-300" : "text-zinc-400"}>
                <ShieldCheck className="mr-1 inline size-3" /> {answer ? `${confidence}% context` : "Ready"}
              </Badge>
            </CardHeader>
            <CardContent>
              {status.length > 0 && (
                <div className="mb-4 grid gap-2 md:grid-cols-3">
                  {status.slice(-3).map((item) => (
                    <div key={`${item.label}-${item.detail}`} className="rounded-2xl border border-white/[.06] bg-white/[.025] p-3">
                      <p className="text-xs text-zinc-200">{item.label}</p>
                      <p className="mt-1 text-[11px] leading-4 text-zinc-600">{item.detail}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="min-h-48 whitespace-pre-wrap rounded-2xl border border-white/[.06] bg-black/20 p-5 text-sm leading-7 text-zinc-200">
                {streamedAnswer || "Ask a question to begin. The workspace will fill answer, evidence, graph, timeline, tasks, meetings, dependencies, sources, and confidence panels."}
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Evidence Timeline" icon={Clock3}>
              {timeline.length ? timeline.map((item, index) => (
                <div key={item.id} className="relative flex gap-3 pb-4 last:pb-0">
                  <div className="flex w-12 flex-col items-center">
                    <span className="text-[10px] text-zinc-600">{new Date(item.timestamp).toLocaleDateString()}</span>
                    <span className="mt-2 size-2 rounded-full bg-violet-300" />
                    {index < timeline.length - 1 && <span className="mt-1 h-full w-px bg-white/[.08]" />}
                  </div>
                  <div className="min-w-0">
                    <Badge>{item.source}</Badge>
                    <p className="mt-2 text-xs leading-5 text-zinc-300">{item.content}</p>
                  </div>
                </div>
              )) : <EmptyPanel label="Evidence timeline appears after a query." />}
            </Panel>

            <Panel title="Knowledge Graph" icon={Network}>
              {graphNodes.length ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {graphNodes.map((node) => (
                    <div key={node.id} className="rounded-2xl border border-white/[.06] bg-white/[.025] p-3">
                      <Badge>{node.type}</Badge>
                      <p className="mt-2 line-clamp-2 text-xs text-zinc-200">{node.label}</p>
                    </div>
                  ))}
                </div>
              ) : <EmptyPanel label="Graph entities and relationships appear here." />}
            </Panel>
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <Panel title="Related Tasks" icon={CheckCircle2}>
              <CompactList items={tasks.map((item) => item.text)} empty="Tasks appear after retrieval." />
            </Panel>
            <Panel title="Dependencies & Risks" icon={GitBranch}>
              <CompactList items={risks.map((item) => item.text)} empty="Dependencies and risks appear here." />
            </Panel>
            <Panel title="Sources" icon={Link2}>
              {Object.entries(sources).length ? (
                <div className="space-y-2">
                  {Object.entries(sources).map(([source, count]) => (
                    <div key={source} className="flex items-center justify-between rounded-xl border border-white/[.06] bg-white/[.025] px-3 py-2 text-xs">
                      <span className="text-zinc-300">{source}</span>
                      <span className="text-zinc-600">{count} item(s)</span>
                    </div>
                  ))}
                </div>
              ) : <EmptyPanel label="Source coverage appears after a query." />}
            </Panel>
          </div>
        </div>

        <aside className="space-y-5">
          <Card>
            <CardHeader>
              <div>
                <p className="text-sm font-medium">Right sidebar</p>
                <p className="mt-1 text-xs text-zinc-600">Related memory objects from the latest answer.</p>
              </div>
              <PanelRight className="size-4 text-zinc-600" />
            </CardHeader>
            <CardContent className="space-y-4">
              <SidebarMetric label="Related memories" value={answer?.selected_context.length || 0} />
              <SidebarMetric label="Related people/projects" value={graphNodes.filter((node) => ["person", "project"].includes(node.type)).length} />
              <SidebarMetric label="Deadlines / risks" value={risks.length} />
              <SidebarMetric label="Validated claims" value={answer?.reasoning.claim_validation.validated_claims || 0} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <p className="text-sm font-medium">Prompt history</p>
                <p className="mt-1 text-xs text-zinc-600">Searchable command memory for this session.</p>
              </div>
              <Search className="size-4 text-zinc-600" />
            </CardHeader>
            <CardContent>
              {promptHistory.length ? (
                <div className="space-y-2">
                  {promptHistory.slice(0, 8).map((item) => (
                    <button key={item.id} onClick={() => setPrompt(item.prompt)} className="block w-full rounded-xl border border-white/[.06] bg-white/[.025] px-3 py-2 text-left text-xs text-zinc-400 transition hover:text-zinc-100">
                      {item.prompt}
                    </button>
                  ))}
                </div>
              ) : <EmptyPanel label="Prompt history starts after your first query." />}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <p className="text-sm font-medium">Ingestion</p>
                <p className="mt-1 text-xs text-zinc-600">Drop files anywhere on the command box.</p>
              </div>
              <Upload className="size-4 text-zinc-600" />
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-zinc-500">
              <p>Supported: PDF, DOCX, TXT, Markdown, audio, video, images, JSON.</p>
              <p>Files are saved inside project storage only, then queued through a manifest.</p>
            </CardContent>
          </Card>
        </aside>
      </section>
    </div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="mt-1 text-xs text-zinc-600">Auto-generated from the current answer.</p>
        </div>
        <Icon className="size-4 text-zinc-600" />
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function CompactList({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <EmptyPanel label={empty} />;
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <motion.div key={item} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-white/[.06] bg-white/[.025] p-3 text-xs leading-5 text-zinc-300">
          {item}
        </motion.div>
      ))}
    </div>
  );
}

function EmptyPanel({ label }: { label: string }) {
  return (
    <div className="grid min-h-28 place-items-center rounded-2xl border border-dashed border-white/[.08] bg-white/[.015] p-4 text-center text-xs text-zinc-600">
      {label}
    </div>
  );
}

function SidebarMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/[.06] bg-white/[.025] px-3 py-3">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold text-zinc-100">{value}</span>
    </div>
  );
}
