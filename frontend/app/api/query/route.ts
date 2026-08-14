import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { projectRoot, pythonExecutable, safeFileName, storageRoot } from "@/lib/server/storage";

export const runtime = "nodejs";

type QueryRequest = {
  query?: string;
  dataText?: string;
  dataFileName?: string;
};

function runMemorae(args: string[]) {
  return new Promise<{ stdout: string; stderr: string; code: number | null }>((resolve) => {
    const child = spawn(pythonExecutable(), args, {
      cwd: projectRoot(),
      env: {
        ...process.env,
        MEMORAE_STORAGE_ROOT: storageRoot(),
        TMP: path.join(storageRoot(), "temp"),
        TEMP: path.join(storageRoot(), "temp"),
        XDG_CACHE_HOME: path.join(storageRoot(), "cache"),
        HF_HOME: path.join(storageRoot(), "models", "huggingface"),
        TRANSFORMERS_CACHE: path.join(storageRoot(), "models", "huggingface", "transformers"),
        SENTENCE_TRANSFORMERS_HOME: path.join(storageRoot(), "models", "sentence-transformers"),
        TORCH_HOME: path.join(storageRoot(), "models", "torch"),
      },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => resolve({ stdout, stderr, code }));
  });
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

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as QueryRequest;
    const query = body.query?.trim();
    if (!query) {
      return NextResponse.json({ error: "Query is required." }, { status: 400 });
    }
    const dataPath = await maybeWriteInlineData(body);
    const args = ["-B", "run.py", "--query", query, "--stdout-json", "--storage-root", storageRoot()];
    if (dataPath) args.push("--data", dataPath);
    const result = await runMemorae(args);
    if (result.code !== 0) {
      return NextResponse.json(
        { error: "Memorae query failed.", details: result.stderr || result.stdout },
        { status: 500 },
      );
    }
    const parsed = JSON.parse(result.stdout);
    const answer = Array.isArray(parsed) ? parsed[0] : parsed;
    return NextResponse.json({
      answer,
      storageRoot: storageRoot(),
      uploadedDataPath: dataPath,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown query error." },
      { status: 500 },
    );
  }
}
