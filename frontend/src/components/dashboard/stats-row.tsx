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
    color: "text-blue-600",
    bg: "bg-blue-50 dark:bg-blue-900/10",
  },
  {
    label: "Prisfald i dag",
    value: stats?.price_drops_today ?? "—",
    sub: `${stats?.price_increases_today ?? 0} stigninger`,
    icon: ArrowDown,
    color: "text-green-600",
    bg: "bg-green-50 dark:bg-green-900/10",
  },
  {
    label: "Checks i dag",
    value: stats?.checks_today ?? "—",
    sub: "automatiske",
    icon: RefreshCw,
    color: "text-violet-600",
    bg: "bg-violet-50 dark:bg-violet-900/10",
  },
  {
    label: "Fejl / Blokeret",
    value: stats ? `${stats.error_watches} / ${stats.blocked_watches}` : "—",
    sub: "kræver opmærksomhed",
    icon: ShieldAlert,
    color: "text-orange-600",
    bg: "bg-orange-50 dark:bg-orange-900/10",
  },
];

export function StatsRow() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: api.dashboard.stats,
    refetchInterval: 30_000,
  });

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards(stats).map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-border bg-card p-4 flex items-start gap-3"
        >
          <div className={`rounded-md p-2.5 ${card.bg}`}>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </div>
          <div>
            <p className="text-2xl font-semibold tabular-nums">
              {isLoading ? "…" : card.value}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">{card.label}</p>
            <p className="text-xs text-muted-foreground/70">{card.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
