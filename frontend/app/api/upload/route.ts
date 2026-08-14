import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { safeFileName, storageRoot } from "@/lib/server/storage";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const files = form.getAll("files").filter((item): item is File => item instanceof File);
    if (!files.length) {
      return NextResponse.json({ error: "Upload at least one file." }, { status: 400 });
    }

    const uploadDir = path.join(storageRoot(), "uploads");
    const artifactDir = path.join(storageRoot(), "artifacts");
    await mkdir(uploadDir, { recursive: true });
    await mkdir(artifactDir, { recursive: true });

    const saved = [];
    for (const file of files) {
      const id = randomUUID();
      const safeName = `${id}-${safeFileName(file.name)}`;
      const filePath = path.join(uploadDir, safeName);
      const buffer = Buffer.from(await file.arrayBuffer());
      await writeFile(filePath, buffer);
      saved.push({
        id,
        name: file.name,
        type: file.type || "application/octet-stream",
        size: file.size,
        path: filePath,
        status: "queued_for_ingestion",
      });
    }

    const manifestPath = path.join(artifactDir, `upload-manifest-${Date.now()}.json`);
    await writeFile(
      manifestPath,
      JSON.stringify({ createdAt: new Date().toISOString(), files: saved }, null, 2),
      "utf8",
    );

    return NextResponse.json({ files: saved, manifestPath, storageRoot: storageRoot() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed." },
      { status: 500 },
    );
  }
}
