import path from "node:path";

export function projectRoot() {
  return path.basename(process.cwd()) === "frontend" ? path.resolve(process.cwd(), "..") : process.cwd();
}

export function storageRoot() {
  return path.join(projectRoot(), "storage");
}

export function pythonExecutable() {
  return process.env.MEMORAE_PYTHON || "python";
}

export function safeFileName(name: string) {
  return name.replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120) || "upload";
}
