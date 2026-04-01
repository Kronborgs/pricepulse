"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, ExternalLink, Pause, Pencil, Play, RefreshCw, Trash2, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { WatchSource, SourceStatus } from "@/types";
import { StatusBadge } from "./status-badge";
import { formatPrice, formatRelative, getDomain } from "@/lib/utils";
import { api } from "@/lib/api";
import { useExchangeRates } from "@/hooks/useExchangeRates";

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
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUrl, setEditUrl] = useState("");

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
  const updateMutation = useMutation({
    mutationFn: ({ id, url }: { id: string; url: string }) =>
      api.sources.update(id, { url }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["product-watch", watchId] });
      setEditingId(null);
    },
  });

  const { data: fxData } = useExchangeRates();

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
              const isEditing = editingId === src.id;
              return (
                <tr key={src.id} className={`group hover:bg-slate-800/50 transition-colors ${isBest ? "bg-[#8DC63F]/5" : ""}`}>
                  <td className="px-4 py-3">
                    {isEditing ? (
                      <div className="flex items-center gap-1.5">
                        <input
                          type="url"
                          value={editUrl}
                          onChange={(e) => setEditUrl(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && editUrl.trim()) updateMutation.mutate({ id: src.id, url: editUrl.trim() });
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          autoFocus
                          className="w-full rounded border border-input bg-slate-800 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                        />
                        <button
                          onClick={() => updateMutation.mutate({ id: src.id, url: editUrl.trim() })}
                          disabled={!editUrl.trim() || updateMutation.isPending}
                          title="Gem"
                          className="p-1 rounded text-[#8DC63F] hover:bg-[#8DC63F]/10 disabled:opacity-40"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          title="Annuller"
                          className="p-1 rounded text-muted-foreground hover:bg-muted"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        {isBest && (
                          <span className="inline-flex items-center rounded-full bg-[#8DC63F]/15 text-[#8DC63F] px-1.5 py-0.5 text-xs font-medium">
                            Bedst
                          </span>
                        )}
                        <Link href={`/sources/${src.id}`} className="font-medium hover:underline">
                          {getDomain(src.url)}
                        </Link>
                        <button
                          onClick={() => { setEditUrl(src.url); setEditingId(src.id); }}
                          title="Rediger URL"
                          className="p-0.5 rounded text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold">
                    {src.last_price != null ? (
                      <div className="flex flex-col items-end gap-0.5">
                        <span>{formatPrice(src.last_price)}</span>
                        {src.last_currency !== "DKK" && src.last_price_raw != null && (
                          <span className="text-xs font-normal text-muted-foreground">
                            {formatPrice(src.last_price_raw, src.last_currency)}
                            {fxData?.rates[src.last_currency] && (
                              <> &middot; 1 {src.last_currency} = {fxData.rates[src.last_currency].toFixed(2)} kr</>
                            )}
                          </span>
                        )}
                      </div>
                    ) : "—"}
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
                        onClick={() => { setEditUrl(src.url); setEditingId(src.id); }}
                        disabled={isEditing}
                        title="Rediger URL"
                        className="p-1.5 rounded hover:bg-slate-700/50 disabled:opacity-40 transition-colors text-muted-foreground"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
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
      {fxData && (() => {
        const foreignCurrencies = [...new Set(
          active
            .filter((s) => s.last_currency !== "DKK" && s.last_price_raw != null)
            .map((s) => s.last_currency)
        )];
        if (foreignCurrencies.length === 0) return null;
        return (
          <p className="text-xs text-muted-foreground px-5 py-2 border-t border-border">
            Kurser fra Danmarks Nationalbank
            {foreignCurrencies.map((c) =>
              fxData.rates[c] ? ` · 1 ${c} = ${fxData.rates[c].toFixed(2)} kr` : ""
            ).join("")}
          </p>
        );
      })()}
    </div>
  );
}
