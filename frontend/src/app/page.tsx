"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatsRow } from "@/components/dashboard/stats-row";
import { RecentChanges } from "@/components/dashboard/recent-changes";
import { StatusBadge } from "@/components/watches/status-badge";

export default function DashboardPage() {
  const { data: watches } = useQuery({
    queryKey: ["watches-errors"],
    queryFn: () =>
      api.watches.list({ status: "error", page: 1, page_size: 10 }),
    refetchInterval: 60_000,
  });

  const errorWatches = watches?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overblik over dine prisovervågninger
        </p>
      </div>

      <StatsRow />

      {errorWatches.length > 0 && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-destructive" />
            <span className="text-sm font-medium text-destructive">
              {errorWatches.length} watch{errorWatches.length !== 1 ? "es" : ""}{" "}
              har fejl
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {errorWatches.map((w) => (
              <Link
                key={w.id}
                href={`/watches/${w.id}`}
                className="inline-flex items-center gap-1.5 rounded-md border bg-background px-2.5 py-1 text-xs hover:bg-muted"
              >
                <StatusBadge status={w.status} />
                <span className="truncate max-w-[180px]">
                  {w.title ?? w.url}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentChanges />
        </div>
        <div>
          <QuickStats />
        </div>
      </div>
    </div>
  );
}

function QuickStats() {
  const { data } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: api.dashboard.stats,
    refetchInterval: 30_000,
  });

  if (!data) return null;

  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-4">
      <h2 className="text-base font-semibold">Hurtig overblik</h2>
      <dl className="space-y-3">
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">Fejl / Blokeret</dt>
          <dd className="font-medium tabular-nums">
            {data.error_watches} / {data.blocked_watches}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">Prisfald i dag</dt>
          <dd className="font-medium tabular-nums text-green-600">
            {data.price_drops_today}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">Prisstigninger</dt>
          <dd className="font-medium tabular-nums text-red-500">
            {data.price_increases_today}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">Produkter i alt</dt>
          <dd className="font-medium tabular-nums">{data.total_products}</dd>
        </div>
      </dl>

      <Link
        href="/watches"
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mt-2"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Se alle watches
      </Link>
    </div>
  );
}
