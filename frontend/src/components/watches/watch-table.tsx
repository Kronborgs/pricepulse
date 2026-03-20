"use client";

import Link from "next/link";
import { ExternalLink, RefreshCw, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Watch } from "@/types";
import { StatusBadge } from "./status-badge";
import { formatPrice, formatRelative, getDomain } from "@/lib/utils";
import { api } from "@/lib/api";

interface Props {
  watches: Watch[];
  isLoading: boolean;
}

export function WatchTable({ watches, isLoading }: Props) {
  const qc = useQueryClient();

  const checkMutation = useMutation({
    mutationFn: (id: string) => api.watches.triggerCheck(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watches"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.watches.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watches"] }),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border">
        <div className="p-8 text-center text-sm text-muted-foreground">
          Indlæser watches…
        </div>
      </div>
    );
  }

  if (watches.length === 0) {
    return (
      <div className="rounded-lg border border-border">
        <div className="p-12 text-center text-sm text-muted-foreground">
          Ingen watches fundet. Tilføj din første watch ovenfor.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Produkt</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Butik</th>
            <th className="text-right px-4 py-3 font-medium text-muted-foreground">Pris</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Lager</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
            <th className="text-left px-4 py-3 font-medium text-muted-foreground">Sidst tjekket</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {watches.map((watch, i) => (
            <tr
              key={watch.id}
              className={`border-b border-border last:border-0 hover:bg-muted/20 transition-colors ${
                i % 2 === 0 ? "" : "bg-muted/10"
              }`}
            >
              <td className="px-4 py-3">
                <Link
                  href={`/watches/${watch.id}`}
                  className="font-medium hover:underline line-clamp-1 max-w-xs block"
                >
                  {watch.title ?? getDomain(watch.url)}
                </Link>
                <span className="text-xs text-muted-foreground truncate max-w-xs block">
                  {getDomain(watch.url)}
                </span>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {watch.shop?.name ?? "—"}
              </td>
              <td className="px-4 py-3 text-right font-mono font-medium tabular-nums">
                {formatPrice(watch.current_price, watch.current_currency)}
              </td>
              <td className="px-4 py-3">
                {watch.current_stock_status === "in_stock" ? (
                  <span className="text-green-600 text-xs">På lager</span>
                ) : watch.current_stock_status === "out_of_stock" ? (
                  <span className="text-red-500 text-xs">Udsolgt</span>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={watch.status} />
              </td>
              <td className="px-4 py-3 text-muted-foreground text-xs">
                {formatRelative(watch.last_checked_at)}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1 justify-end">
                  <button
                    onClick={() => checkMutation.mutate(watch.id)}
                    disabled={checkMutation.isPending}
                    className="p-1.5 rounded hover:bg-accent disabled:opacity-40"
                    title="Tjek nu"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${checkMutation.isPending ? "animate-spin" : ""}`} />
                  </button>
                  <a
                    href={watch.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-accent"
                    title="Åbn URL"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                  <button
                    onClick={() => {
                      if (confirm("Slet denne watch?")) {
                        deleteMutation.mutate(watch.id);
                      }
                    }}
                    className="p-1.5 rounded hover:bg-destructive/10 text-destructive/60 hover:text-destructive"
                    title="Slet"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
