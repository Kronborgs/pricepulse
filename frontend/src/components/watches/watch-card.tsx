"use client";

import Link from "next/link";
import Image from "next/image";
import { ExternalLink, RefreshCw } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Watch } from "@/types";
import { StatusBadge } from "./status-badge";
import { formatPrice, formatRelative, getDomain } from "@/lib/utils";
import { api } from "@/lib/api";

interface Props {
  watch: Watch;
}

export function WatchCard({ watch }: Props) {
  const qc = useQueryClient();
  const checkMutation = useMutation({
    mutationFn: () => api.watches.triggerCheck(watch.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watches"] });
    },
  });

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3 hover:shadow-sm transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          {watch.image_url ? (
            <Image
              src={watch.image_url}
              alt={watch.title ?? "Produktbillede"}
              width={48}
              height={48}
              className="rounded-md object-contain flex-shrink-0 bg-secondary"
            />
          ) : (
            <div className="h-12 w-12 flex-shrink-0 rounded-md bg-secondary" />
          )}
          <div className="min-w-0">
            <Link
              href={`/watches/${watch.id}`}
              className="text-sm font-medium leading-tight line-clamp-2 hover:underline"
            >
              {watch.title ?? getDomain(watch.url)}
            </Link>
            {watch.shop && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {watch.shop.name}
              </p>
            )}
          </div>
        </div>
        <StatusBadge status={watch.status} />
      </div>

      {/* Price */}
      <div className="flex items-end gap-2">
        <span className="text-2xl font-semibold tabular-nums">
          {formatPrice(watch.current_price, watch.current_currency)}
        </span>
        {watch.current_stock_status && (
          <span className="text-xs text-muted-foreground mb-1">
            {watch.current_stock_status === "in_stock"
              ? "På lager"
              : watch.current_stock_status === "out_of_stock"
              ? "Udsolgt"
              : watch.current_stock_status}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Tjekket {formatRelative(watch.last_checked_at)}</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            title="Tjek nu"
            className="p-1 rounded hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${checkMutation.isPending ? "animate-spin" : ""}`}
            />
          </button>
          <a
            href={watch.url}
            target="_blank"
            rel="noopener noreferrer"
            title="Åbn i butik"
            className="p-1 rounded hover:bg-accent"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {/* Error */}
      {watch.last_error && watch.status !== "active" && (
        <p className="text-xs text-destructive line-clamp-2 bg-destructive/10 rounded px-2 py-1">
          {watch.last_error}
        </p>
      )}
    </div>
  );
}
