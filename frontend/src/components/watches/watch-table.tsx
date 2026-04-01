"use client";

import Link from "next/link";
import { ExternalLink, RefreshCw, Trash2, User } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Watch } from "@/types";
import { StatusBadge } from "./status-badge";
import { formatPrice, formatRelative, getDomain } from "@/lib/utils";
import { api } from "@/lib/api";

interface Props {
  watches: Watch[];
  isLoading: boolean;
  showOwner?: boolean;
}

function ConfirmDeleteDialog({
  watch,
  onConfirm,
  onCancel,
  isPending,
}: {
  watch: Watch;
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative z-10 w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="rounded-full bg-destructive/15 p-2.5">
            <Trash2 className="h-5 w-5 text-destructive" />
          </div>
          <h2 className="text-base font-semibold">Slet watch?</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-1">
          {watch.title ?? getDomain(watch.url)}
        </p>
        <p className="text-xs text-muted-foreground mb-6">
          Handlingen kan ikke fortrydes. Al prishistorik for denne watch slettes permanent.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="flex-1 rounded-md border border-border px-4 py-2 text-sm hover:bg-muted transition-colors disabled:opacity-50"
          >
            Annuller
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
          >
            {isPending ? "Sletter…" : "Ja, slet"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function WatchTable({ watches, isLoading, showOwner }: Props) {
  const qc = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Watch | null>(null);

  const checkMutation = useMutation({
    mutationFn: (id: string) => api.watches.triggerCheck(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watches"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.watches.delete(id),
    onSettled: () => {
      setDeleteTarget(null);
      qc.invalidateQueries({ queryKey: ["watches"] });
    },
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
            {showOwner && <th className="text-left px-4 py-3 font-medium text-muted-foreground">Ejer</th>}
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
                {formatPrice(watch.current_price)}
              </td>
              <td className="px-4 py-3">
                {watch.current_stock_status === "in_stock" ? (
                  <span className="text-green-600 text-xs">På lager</span>
                ) : watch.current_stock_status === "out_of_stock" ? (
                  <span className="text-red-500 text-xs">Udsolgt</span>
                ) : (
                  <span className="text-muted-foreground text-xs">Lagerstatus kendes ikke</span>
                )}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={watch.status} />
              </td>
              {showOwner && (
                <td className="px-4 py-3">
                  {watch.owner_name ? (
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400">
                      <User className="h-3 w-3" />{watch.owner_name}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">System</span>
                  )}
                </td>
              )}
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
                    onClick={() => setDeleteTarget(watch)}
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

      {deleteTarget && (
        <ConfirmDeleteDialog
          watch={deleteTarget}
          isPending={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
