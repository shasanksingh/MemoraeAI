import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { projectRoot, pythonExecutable, safeFileName, storageRoot } from "@/lib/server/storage";

export const runtime = "nodejs";

type QueryRequest = {
  query?: string;
  dataText?: string;
  dataFileName?: string;
};

const encoder = new TextEncoder();

function sse(event: string, data: unknown) {
  return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

async function maybeWriteInlineData(body: QueryRequest) {
  if (!body.dataText?.trim()) return null;
  const uploadDir = path.join(storageRoot(), "uploads");
  await mkdir(uploadDir, { recursive: true });
  const name = safeFileName(body.dataFileName || `manual-events-${randomUUID()}.json`);
  const filePath = path.join(uploadDir, name.endsWith(".json") ? name : `${name}.json`);
  JSON.parse(body.dataText);
  await writeFile(filePath, body.dataText, "utf8");
  return filePath;
}

function memoraeEnv() {
  return {
    ...process.env,
    MEMORAE_STORAGE_ROOT: storageRoot(),
    TMP: path.join(storageRoot(), "temp"),
    TEMP: path.join(storageRoot(), "temp"),
    XDG_CACHE_HOME: path.join(storageRoot(), "cache"),
    HF_HOME: path.join(storageRoot(), "models", "huggingface"),
    TRANSFORMERS_CACHE: path.join(storageRoot(), "models", "huggingface", "transformers"),
    SENTENCE_TRANSFORMERS_HOME: path.join(storageRoot(), "models", "sentence-transformers"),
    TORCH_HOME: path.join(storageRoot(), "models", "torch"),
  };
}

export async function POST(request: Request) {
  const body = (await request.json()) as QueryRequest;
  const query = body.query?.trim();
  if (!query) {
    return new Response(encoder.encode("event: error\ndata: {\"error\":\"Query is required.\"}\n\n"), {
      status: 400,
      headers: { "Content-Type": "text/event-stream" },
    });
  }
  const dataPath = await maybeWriteInlineData(body);

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(sse("status", { label: "Planning retrieval", detail: "Detecting query facets and evidence needs." }));
      const args = ["-B", "run.py", "--query", query, "--stdout-json", "--storage-root", storageRoot()];
      if (dataPath) args.push("--data", dataPath);
      const child = spawn(pythonExecutable(), args, {
        cwd: projectRoot(),
        env: memoraeEnv(),
      });
      let stdout = "";
      let stderr = "";
      const timers = [
        setTimeout(() => controller.enqueue(sse("status", { label: "Searching memory", detail: "Running broad recall over raw events." })), 350),
        setTimeout(() => controller.enqueue(sse("status", { label: "Expanding evidence", detail: "Following graph, timeline, and dependency links." })), 900),
        setTimeout(() => controller.enqueue(sse("status", { label: "Building context", detail: "Scoring coverage and assembling answer panels." })), 1400),
      ];
      child.stdout.on("data", (chunk) => {
        stdout += chunk.toString();
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk.toString();
      });
      child.on("close", (code) => {
        timers.forEach(clearTimeout);
        if (code !== 0) {
          controller.enqueue(sse("error", { error: "Memorae query failed.", details: stderr || stdout }));
          controller.close();
          return;
        }
        try {
          const parsed = JSON.parse(stdout);
          const answer = Array.isArray(parsed) ? parsed[0] : parsed;
          const words = String(answer.answer || "").split(/\s+/);
          for (let index = 0; index < words.length; index += 18) {
            controller.enqueue(sse("token", { text: `${words.slice(index, index + 18).join(" ")} ` }));
          }
          controller.enqueue(sse("final", { answer, storageRoot: storageRoot(), uploadedDataPath: dataPath }));
        } catch (error) {
          controller.enqueue(sse("error", { error: error instanceof Error ? error.message : "Could not parse Memorae output." }));
        }
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
