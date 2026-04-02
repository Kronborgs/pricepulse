"use client";

import { useQuery } from "@tanstack/react-query";
import { DashboardStats } from "@/types";
import { api } from "@/lib/api";
import {
  ArrowDown,
  Eye,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useI18n } from "@/lib/i18n";

function useStatCards(
  stats: DashboardStats | undefined,
  t: (k: string, v?: Record<string, string | number>) => string
) {
  return [
    {
      label: t("stats_active_watches"),
      value: stats?.active_watches ?? "\u2014",
      sub: t("stats_total_n", { n: stats?.total_watches ?? 0 }),
      icon: Eye,
      color: "text-[#29ABE2]",
      bg: "bg-[#29ABE2]/10",
      topBorder: "border-t-[#29ABE2]",
    },
    {
      label: t("stats_price_drops"),
      value: stats?.price_drops_today ?? "\u2014",
      sub: t("stats_increases", { n: stats?.price_increases_today ?? 0 }),
      icon: ArrowDown,
      color: "text-[#8DC63F]",
      bg: "bg-[#8DC63F]/10",
      topBorder: "border-t-[#8DC63F]",
    },
    {
      label: t("stats_checks_today"),
      value: stats?.checks_today ?? "\u2014",
      sub: t("stats_automatic"),
      icon: RefreshCw,
      color: "text-[#29ABE2]",
      bg: "bg-[#29ABE2]/10",
      topBorder: "border-t-[#29ABE2]",
    },
    {
      label: t("stats_errors_blocked"),
      value: stats ? `${stats.error_watches} / ${stats.blocked_watches}` : "\u2014",
      sub: t("stats_needs_attention"),
      icon: ShieldAlert,
      color: "text-[#F7941D]",
      bg: "bg-[#F7941D]/10",
      topBorder: "border-t-[#F7941D]",
    },
  ];
}

export function StatsRow({ ownerId }: { ownerId?: string }) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats", ownerId],
    queryFn: () => api.dashboard.stats(ownerId),
    refetchInterval: 30_000,
  });
  const { t } = useI18n();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const statCards = useStatCards(stats, t as any);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((card) => (
        <div
          key={card.label}
          className={`rounded-xl border border-border bg-card p-4 flex items-start gap-3 shadow-sm border-t-2 ${card.topBorder}`}
        >
          <div className={`rounded-lg p-2.5 flex-shrink-0 ${card.bg}`}>
            <card.icon className={`h-5 w-5 ${card.color}`} />
          </div>
          <div>
            <p className="text-2xl font-bold tabular-nums">
              {isLoading ? "\u2026" : card.value}
            </p>
            <p className={`text-xs font-semibold mt-0.5 ${card.color}`}>{card.label}</p>
            <p className="text-xs text-muted-foreground/70">{card.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
