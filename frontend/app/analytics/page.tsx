import { AnalyticsChart } from "@/components/analytics-chart";
import { PageHeading } from "@/components/page-heading";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function AnalyticsPage() { return <><PageHeading eyebrow="Patterns" title="Analytics Center" description="Understand completion, focus, procrastination, meeting load, and project health without turning your life into vanity metrics." /><div className="grid gap-4 md:grid-cols-4">{[["76%","Completion rate"],["3.4h","Deep work / day"],["11%","Commitment drift"],["8.2h","Meeting load"]].map(([value,label]) => <Card key={label} className="p-4"><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-zinc-600">{label}</p></Card>)}</div><Card className="mt-5"><CardHeader><div><p className="text-sm">Focus quality</p><p className="mt-1 text-xs text-zinc-600">Evidence-weighted daily trend</p></div></CardHeader><CardContent><AnalyticsChart /></CardContent></Card></>; }
