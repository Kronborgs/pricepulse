"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Flag, RefreshCw } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatsRow } from "@/components/dashboard/stats-row";
import { RecentChanges } from "@/components/dashboard/recent-changes";
import { StatusBadge } from "@/components/watches/status-badge";
import { UserFilterDropdown } from "@/components/ui/user-filter-dropdown";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useI18n } from "@/lib/i18n";

const LS_KEY = "dashboard_owner_filter";

export default function DashboardPage() {
  const { data: me } = useCurrentUser();
  const { t } = useI18n();
  const isAdmin = me?.role === "admin";
  const isPrivileged = me?.role === "admin" || me?.role === "superuser";

  // Admin can pick which user's data to view (single-select, persisted)
  const [ownerFilter, setOwnerFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!me || !isAdmin) return;
    const saved = localStorage.getItem(LS_KEY);
    setOwnerFilter(saved ?? me.id);
  }, [me, isAdmin]);

  const { data: usersData } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.adminUsers.list({ limit: 200 }),
    enabled: isAdmin,
  });

  // The user whose data is being shown
  const viewingUserId: string | undefined = isAdmin
    ? (ownerFilter ?? me?.id)
    : me?.id;

  // Only pass owner_id to stats/recent-events when admin views another user
  // (backend always defaults to self for non-admin and admin without param)
  const apiOwnerId =
    isAdmin && viewingUserId && viewingUserId !== me?.id
      ? viewingUserId
      : undefined;

  const { data: watches } = useQuery({
    queryKey: ["watches-errors", viewingUserId],
    queryFn: () =>
      api.watches.list({
        status: "error",
        skip: 0,
        limit: 10,
        // Explicit filter needed for privileged roles since backend shows all otherwise
        owner_ids: isPrivileged && viewingUserId ? [viewingUserId] : undefined,
      }),
    enabled: !!me,
    refetchInterval: 60_000,
  });

  const { data: unreadData } = useQuery({
    queryKey: ["reports-unread"],
    queryFn: () => api.reports.unreadCount(),
    enabled: isPrivileged,
    refetchInterval: 60_000,
  });

  const errorWatches = watches?.items ?? [];
  const unreadReports = unreadData?.count ?? 0;

  function handleOwnerChange(ids: string[]) {
    const current = ownerFilter ? [ownerFilter] : [];
    const newId = ids.find((id) => !current.includes(id));
    const next = newId ?? ids[0] ?? me?.id ?? null;
    setOwnerFilter(next ?? null);
    if (next && next !== me?.id) {
      localStorage.setItem(LS_KEY, next);
    } else {
      localStorage.removeItem(LS_KEY);
    }
  }

  const selectedIds = ownerFilter ? [ownerFilter] : [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("dashboard_title")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("dashboard_subtitle")}
          </p>
        </div>
        {isAdmin && (usersData?.items ?? []).length > 0 && (
          <UserFilterDropdown
            users={usersData?.items ?? []}
            selected={selectedIds}
            onChange={handleOwnerChange}
          />
        )}
      </div>

      <StatsRow ownerId={apiOwnerId} />

      {errorWatches.length > 0 && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <span className="text-sm font-medium text-red-400">
              {t("dashboard_watches_have_errors", { n: errorWatches.length })}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {errorWatches.map((w) => (
              <Link
                key={w.id}
                href={`/watches/${w.id}`}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs hover:bg-slate-700/60"
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

      {isPrivileged && unreadReports > 0 && (
        <Link
          href="/admin/reports"
          className="flex items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 hover:bg-amber-500/15 transition-colors"
        >
          <Flag className="h-4 w-4 text-amber-400 shrink-0" />
          <span className="text-sm text-amber-300">
            {t("dashboard_new_scraper_reports", { n: unreadReports })}
          </span>
        </Link>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentChanges ownerId={apiOwnerId} />
        </div>
        <div>
          <QuickStats ownerId={apiOwnerId} />
        </div>
      </div>
    </div>
  );
}

function QuickStats({ ownerId }: { ownerId?: string }) {
  const { data } = useQuery({
    queryKey: ["dashboard-stats", ownerId],
    queryFn: () => api.dashboard.stats(ownerId),
    refetchInterval: 30_000,
  });
  const { t } = useI18n();

  if (!data) return null;

  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-4">
      <h2 className="text-sm font-semibold text-slate-300">{t("dashboard_quick_overview")}</h2>
      <dl className="space-y-3">
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">{t("dashboard_errors_blocked")}</dt>
          <dd className="font-medium tabular-nums">
            {data.error_watches} / {data.blocked_watches}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">{t("dashboard_price_drops")}</dt>
          <dd className="font-medium tabular-nums text-[#8DC63F]">
            {data.price_drops_today}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">{t("dashboard_price_increases")}</dt>
          <dd className="font-medium tabular-nums text-red-400">
            {data.price_increases_today}
          </dd>
        </div>
        <div className="flex justify-between text-sm">
          <dt className="text-muted-foreground">{t("dashboard_products_total")}</dt>
          <dd className="font-medium tabular-nums">{data.total_products}</dd>
        </div>
      </dl>

      <Link
        href="/watches"
        className="flex items-center gap-1.5 text-xs text-[#29ABE2] hover:text-[#29ABE2]/80 mt-2"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        {t("dashboard_see_all_watches")}
      </Link>
    </div>
  );
}

