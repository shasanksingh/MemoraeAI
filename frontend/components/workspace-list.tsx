import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export function WorkspaceList({ items }: { items: Array<{ title: string; type: string; meta: string }> }) {
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <Card key={item.title} className="flex items-center gap-4 p-4 transition hover:-translate-y-0.5 hover:border-white/[.13]">
          <div className="min-w-0 flex-1">
            <div className="mb-2">
              <Badge>{item.type}</Badge>
            </div>
            <p className="truncate text-sm text-zinc-200">{item.title}</p>
            <p className="mt-1 text-xs text-zinc-600">{item.meta}</p>
          </div>
          <span className="text-zinc-700">-&gt;</span>
        </Card>
      ))}
    </div>
  );
}
