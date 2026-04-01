"use client";

import { useQuery } from "@tanstack/react-query";
import { DashboardStats } from "@/types";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Eye,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

const statCards = (stats: DashboardStats | undefined) => [
  {
    label: "Aktive watches",
    value: stats?.active_watches ?? "—",
    sub: `${stats?.total_watches ?? 0} i alt`,
    icon: Eye,
    color: "text-[#29ABE2]",
    bg: "bg-[#29ABE2]/10",
    topBorder: "border-t-[#29ABE2]",
  },
  {
    label: "Prisfald i dag",
    value: stats?.price_drops_today ?? "—",
    sub: `${stats?.price_increases_today ?? 0} stigninger`,
    icon: ArrowDown,
    color: "text-[#8DC63F]",
    bg: "bg-[#8DC63F]/10",
    topBorder: "border-t-[#8DC63F]",
  },
  {
    label: "Checks i dag",
    value: stats?.checks_today ?? "—",
    sub: "automatiske",
    icon: RefreshCw,
    color: "text-[#29ABE2]",
    bg: "bg-[#29ABE2]/10",
    topBorder: "border-t-[#29ABE2]",
  },
  {
    label: "Fejl / Blokeret",
    value: stats ? `${stats.error_watches} / ${stats.blocked_watches}` : "—",
    sub: "kræver opmærksomhed",
    icon: ShieldAlert,
    color: "text-[#F7941D]",
    bg: "bg-[#F7941D]/10",
    topBorder: "border-t-[#F7941D]",
  },
];

export function StatsRow({ ownerId }: { ownerId?: string }) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats", ownerId],
    queryFn: () => api.dashboard.stats(ownerId),
    refetchInterval: 30_000,
  });

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards(stats).map((card) => (
        <div
          key={card.label}
          className={`rounded-xl border border-border bg-card p-4 flex items-start gap-3 shadow-sm border-t-2 ${card.topBorder}`}
        >
          <div className={`rounded-lg p-2.5 flex-shrink-0 ${card.bg}`}>
            <card.icon className={`h-5 w-5 ${card.color}`} />
          </div>
          <div>
            <p className="text-2xl font-bold tabular-nums">
              {isLoading ? "…" : card.value}
            </p>
            <p className={`text-xs font-semibold mt-0.5 ${card.color}`}>{card.label}</p>
            <p className="text-xs text-muted-foreground/70">{card.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
