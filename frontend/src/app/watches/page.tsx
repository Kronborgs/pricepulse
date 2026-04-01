"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { WatchTable } from "@/components/watches/watch-table";
import { AddWatchDialog } from "@/components/watches/add-watch-dialog";
import { UserFilterDropdown } from "@/components/ui/user-filter-dropdown";
import { Watch } from "@/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";

const STATUS_OPTIONS = [
  { value: "", label: "Alle" },
  { value: "active", label: "Aktive" },
  { value: "pending", label: "Afventer" },
  { value: "ai_analyzing", label: "AI analyserer" },
  { value: "paused", label: "Pausede" },
  { value: "error", label: "Fejl" },
  { value: "blocked", label: "Blokeret" },
];

const OWNER_FILTER_KEY = "watches_owner_filter";

export default function WatchesPage() {
  const { data: me } = useCurrentUser();
  const isPrivileged = me?.role === "admin" || me?.role === "superuser";

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [ownerFilter, setOwnerFilter] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = localStorage.getItem(OWNER_FILTER_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [page, setPage] = useState(1);

  // Gem ownerFilter i localStorage når det ændres
  useEffect(() => {
    try {
      if (ownerFilter.length > 0) {
        localStorage.setItem(OWNER_FILTER_KEY, JSON.stringify(ownerFilter));
      } else {
        localStorage.removeItem(OWNER_FILTER_KEY);
      }
    } catch { /* ignore */ }
  }, [ownerFilter]);

  // Hent brugerliste til filterdropdown (kun for admin/superuser)
  const { data: usersData } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.adminUsers.list({ limit: 100 }),
    enabled: isPrivileged,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["watches", { search, status, page, ownerFilter }],
    queryFn: () =>
      api.watches.list({
        search: search || undefined,
        status: status || undefined,
        skip: (page - 1) * 25,
        limit: 25,
        owner_ids: ownerFilter.length ? ownerFilter : undefined,
      }),
    refetchInterval: 30_000,
  });

  const watches: Watch[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 25));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Data webscraper</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} overvågede priser
          </p>
        </div>
        <AddWatchDialog />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="search"
            placeholder="Søg på URL eller navn…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="h-9 w-64 rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex items-center gap-1">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setStatus(opt.value);
                setPage(1);
              }}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                status === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {isPrivileged && (
          <div className="ml-auto">
            <UserFilterDropdown
              users={usersData?.items ?? []}
              selected={ownerFilter}
              onChange={(ids) => { setOwnerFilter(ids); setPage(1); }}
            />
          </div>
        )}
      </div>

      <WatchTable
        watches={watches}
        isLoading={isLoading}
        showOwner={isPrivileged}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md border px-3 py-1.5 disabled:opacity-40 hover:bg-muted transition-colors"
          >
            Forrige
          </button>
          <span className="text-muted-foreground">
            Side {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md border px-3 py-1.5 disabled:opacity-40 hover:bg-muted transition-colors"
          >
            Næste
          </button>
        </div>
      )}
    </div>
  );
}
