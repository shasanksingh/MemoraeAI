"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { trendData } from "@/lib/data";

export function AnalyticsChart() {
  return <div className="h-[320px] w-full"><ResponsiveContainer><AreaChart data={trendData}><defs><linearGradient id="focus" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8b5cf6" stopOpacity={.35}/><stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#ffffff0b" vertical={false}/><XAxis dataKey="day" tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: "#12151f", border: "1px solid #ffffff12", borderRadius: 12, fontSize: 12 }}/><Area type="monotone" dataKey="focus" stroke="#8b5cf6" strokeWidth={2} fill="url(#focus)" /></AreaChart></ResponsiveContainer></div>;
}
