"use client";

import Link from "next/link";
import { ExternalLink, Pause, Play, RefreshCw, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { WatchSource, SourceStatus } from "@/types";
import { StatusBadge } from "./status-badge";
import { formatPrice, formatRelative, getDomain } from "@/lib/utils";
import { api } from "@/lib/api";

const STOCK_LABELS: Record<string, string> = {
  in_stock: "På lager",
  out_of_stock: "Udsolgt",
  preorder: "Forudbestilling",
  unknown: "—",
};

interface Props {
  sources: WatchSource[];
  bestSourceId: string | null;
  watchId: string;
}

export function PriceComparisonTable({ sources, bestSourceId, watchId }: Props) {
  const qc = useQueryClient();

  const pauseMutation = useMutation({
    mutationFn: (id: string) => api.sources.pause(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["product-watch", watchId] }),
  });
  const resumeMutation = useMutation({
    mutationFn: (id: string) => api.sources.resume(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["product-watch", watchId] }),
  });
  const checkMutation = useMutation({
    mutationFn: (id: string) => api.sources.check(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["product-watch", watchId] }),
  });
  const archiveMutation = useMutation({
    mutationFn: (id: string) => api.sources.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["product-watch", watchId] }),
  });

  const active = sources.filter((s) => s.status !== "archived");

  if (active.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted-foreground">
        Ingen aktive kilder
      </div>
    );
  }

  const sorted = [...active].sort((a, b) => {
    if (a.last_price == null && b.last_price == null) return 0;
    if (a.last_price == null) return 1;
    if (b.last_price == null) return -1;
    return a.last_price - b.last_price;
  });

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <h2 className="text-base font-semibold">Prissammenligning</h2>
        <span className="text-xs text-muted-foreground">{active.length} kilde{active.length !== 1 ? "r" : ""}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Butik</th>
              <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Pris</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground hidden sm:table-cell">Lager</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground hidden md:table-cell">Status</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground hidden lg:table-cell">Sidst tjekket</th>
              <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Handlinger</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sorted.map((src) => {
              const isBest = src.id === bestSourceId;
              const isWorking = pauseMutation.isPending || resumeMutation.isPending || checkMutation.isPending;
              return (
                <tr key={src.id} className={`hover:bg-slate-800/50 transition-colors ${isBest ? "bg-[#8DC63F]/5" : ""}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {isBest && (
                        <span className="inline-flex items-center rounded-full bg-[#8DC63F]/15 text-[#8DC63F] px-1.5 py-0.5 text-xs font-medium">
                          Bedst
                        </span>
                      )}
                      <Link href={`/sources/${src.id}`} className="font-medium hover:underline">
                        {getDomain(src.url)}
                      </Link>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold">
                    {src.last_price != null ? formatPrice(src.last_price, src.last_currency) : "—"}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell text-muted-foreground">
                    {STOCK_LABELS[src.last_stock_status ?? "unknown"] ?? src.last_stock_status ?? "—"}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <StatusBadge status={src.status} />
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell text-muted-foreground tabular-nums">
                    {formatRelative(src.last_check_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => checkMutation.mutate(src.id)}
                        disabled={isWorking}
                        title="Tjek nu"
                        className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${checkMutation.isPending ? "animate-spin" : ""}`} />
                      </button>
                      {src.status === "paused" ? (
                        <button
                          onClick={() => resumeMutation.mutate(src.id)}
                          disabled={isWorking}
                          title="Genoptag"
                          className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors text-green-600"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => pauseMutation.mutate(src.id)}
                          disabled={isWorking || src.status === "archived"}
                          title="Sæt på pause"
                          className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors"
                        >
                          <Pause className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Åbn i butik"
                        className="p-1.5 rounded hover:bg-accent transition-colors"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      <button
                        onClick={() => {
                          if (confirm(`Arkivér ${getDomain(src.url)}?`)) {
                            archiveMutation.mutate(src.id);
                          }
                        }}
                        disabled={isWorking}
                        title="Arkivér"
                        className="p-1.5 rounded hover:bg-accent disabled:opacity-40 transition-colors text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
