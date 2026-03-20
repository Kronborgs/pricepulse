"use client";

import { useQuery } from "@tanstack/react-query";
import { useQueryState } from "nuqs";
import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { WatchTable } from "@/components/watches/watch-table";
import { AddWatchDialog } from "@/components/watches/add-watch-dialog";
import { Watch } from "@/types";

const STATUS_OPTIONS = [
  { value: "", label: "Alle" },
  { value: "active", label: "Aktive" },
  { value: "pending", label: "Afventer" },
  { value: "paused", label: "Pausede" },
  { value: "error", label: "Fejl" },
  { value: "blocked", label: "Blokeret" },
];

export default function WatchesPage() {
  const [search, setSearch] = useQueryState("search", { defaultValue: "" });
  const [status, setStatus] = useQueryState("status", { defaultValue: "" });
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["watches", { search, status, page }],
    queryFn: () =>
      api.watches.list({
        search: search || undefined,
        status: status || undefined,
        skip: (page - 1) * 25,
        limit: 25,
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
          <h1 className="text-2xl font-bold tracking-tight">Watches</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} overvågede priser
          </p>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Tilføj watch
        </button>
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
              setSearch(e.target.value || null);
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
                setStatus(opt.value || null);
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
      </div>

      <WatchTable
        watches={watches}
        isLoading={isLoading}
        onRefresh={refetch}
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

      <AddWatchDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={refetch}
      />
    </div>
  );
}
