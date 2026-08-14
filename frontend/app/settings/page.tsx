import { PageHeading } from "@/components/page-heading";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const folders = [
  "storage/logs",
  "storage/uploads",
  "storage/database",
  "storage/sqlite",
  "storage/graph",
  "storage/indexes",
  "storage/embeddings",
  "storage/cache",
  "storage/temp",
  "storage/models",
  "storage/artifacts",
  "storage/generated",
  "storage/exports",
];

export default function SettingsPage() {
  return (
    <>
      <PageHeading
        eyebrow="Runtime"
        title="Storage settings"
        description="Memorae keeps logs, uploads, caches, generated files, indexes, databases, and model artifacts inside this project folder."
      />
      <Card>
        <CardHeader>
          <div>
            <p className="text-sm font-medium">Project-local storage</p>
            <p className="mt-1 text-xs text-zinc-600">No root-level D drive folders are created by default.</p>
          </div>
          <Badge>Project only</Badge>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {folders.map((folder) => (
            <div key={folder} className="rounded-2xl border border-white/[.06] bg-white/[.025] p-4 font-mono text-xs text-zinc-400">
              {folder}
            </div>
          ))}
        </CardContent>
      </Card>
    </>
  );
}
