export type EvidenceContext = {
  id: string;
  timestamp: string;
  source: string;
  content: string;
  retrieval?: { score?: number };
  evidence_graph?: {
    evidence_role?: string;
    nodes?: Array<{ id: string; type: string; label: string }>;
    expansion_paths?: Record<string, string[]>;
  };
};

export type SupportedClaim = {
  type: string;
  text: string;
  evidence_ids: string[];
};

export type IntelligenceAnswer = {
  query: string;
  answer: string;
  selected_context: EvidenceContext[];
  reasoning: {
    context_quality: {
      score: number;
      evidence_coverage?: number;
      diversity?: number;
      recency?: number;
      completeness?: number;
      contradiction_resolution?: number;
    };
    claim_validation: {
      valid: boolean;
      validated_claims?: number;
      validated_evidence?: number;
      errors?: string[];
    };
    retrieval_trace?: {
      rounds?: Array<{ round: number; operation: string; candidate_count: number; marginal_gain?: number }>;
      selected_memory_layers?: string[];
      stop_reason?: string;
    };
    supported_claims?: SupportedClaim[];
  };
};

export type QueryResult = {
  answer: IntelligenceAnswer;
  storageRoot: string;
  uploadedDataPath?: string | null;
};

export type StreamEvent =
  | { type: "status"; label: string; detail: string }
  | { type: "token"; text: string }
  | { type: "final"; result: QueryResult }
  | { type: "error"; error: string; details?: string };

export async function askMemory(query: string, dataText?: string): Promise<QueryResult> {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, dataText, dataFileName: "workspace-events.json" }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Query failed (${response.status})`);
  }
  return response.json() as Promise<QueryResult>;
}

export async function streamMemoryQuery(
  query: string,
  dataText: string | undefined,
  onEvent: (event: StreamEvent) => void,
) {
  const response = await fetch("/api/query/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, dataText, dataFileName: "workspace-events.json" }),
  });
  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || `Query failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const messages = buffer.split("\n\n");
    buffer = messages.pop() || "";
    for (const message of messages) {
      const lines = message.split("\n");
      const type = lines.find((line) => line.startsWith("event: "))?.slice(7);
      const dataLine = lines.find((line) => line.startsWith("data: "))?.slice(6);
      if (!type || !dataLine) continue;
      const data = JSON.parse(dataLine);
      if (type === "status") onEvent({ type, label: data.label, detail: data.detail });
      if (type === "token") onEvent({ type, text: data.text });
      if (type === "final") onEvent({ type, result: data });
      if (type === "error") onEvent({ type, error: data.error, details: data.details });
    }
  }
}

export async function uploadFiles(files: File[]) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const response = await fetch("/api/upload", { method: "POST", body: form });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Upload failed (${response.status})`);
  }
  return response.json() as Promise<{
    files: Array<{ id: string; name: string; type: string; size: number; path: string; status: string }>;
    manifestPath: string;
    storageRoot: string;
  }>;
}
