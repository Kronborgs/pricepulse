"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { PriceChart } from "@/components/watches/price-chart";
import { StatusBadge } from "@/components/watches/status-badge";
import { formatPrice, formatRelative } from "@/lib/utils";
import { PriceEvent, ERROR_TYPE_LABELS, WatchDiagnostic } from "@/types";

export default function WatchDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: watch, isLoading } = useQuery({
    queryKey: ["watch", id],
    queryFn: () => api.watches.get(id),
    refetchInterval: 30_000,
  });

  const { data: events } = useQuery({
    queryKey: ["watch-events", id],
    queryFn: () => api.history.events(id, 50),
  });

  const checkMutation = useMutation({
    mutationFn: () => api.watches.triggerCheck(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watch", id] });
      queryClient.invalidateQueries({ queryKey: ["watch-events", id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.watches.delete(id),
    onSuccess: () => router.push("/watches"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!watch) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Watch ikke fundet</p>
        <Link href="/watches" className="text-sm text-primary hover:underline">
          Tilbage til watches
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          href="/watches"
          className="mt-1 rounded-md p-1 hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold truncate">
              {watch.title ?? watch.url}
            </h1>
            <StatusBadge status={watch.status} />
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
            <span>{watch.shop?.name ?? "—"}</span>
            {watch.last_checked_at && (
              <span>Sidst tjekket {formatRelative(watch.last_checked_at)}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <a
            href={watch.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Butik
          </a>
          <button
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${checkMutation.isPending ? "animate-spin" : ""}`}
            />
            Tjek nu
          </button>
          {confirmDelete ? (
            <div className="flex gap-1">
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground hover:bg-destructive/90"
              >
                Bekræft slet
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
              >
                Annuller
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="rounded-md border px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Price summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Aktuel pris">
          {watch.current_price != null
            ? formatPrice(watch.current_price)
            : "—"}
        </StatCard>
        <StatCard label="Lager">
          {watch.current_stock_status ?? "—"}
        </StatCard>
        <StatCard label="Tjekinterval">
          {watch.check_interval
            ? `${watch.check_interval} min`
            : "—"}
        </StatCard>
        <StatCard label="Fejl">
          {watch.error_count ?? 0}
        </StatCard>
      </div>

      {/* Price chart */}
      <div className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-base font-semibold mb-4">Prishistorik</h2>
        <PriceChart watchId={id} />
      </div>

      {/* Diagnostic panel — vis kun ved fejl eller hvis der er diagnostik */}
      {watch.last_diagnostic && (
        <DiagnosticPanel diagnostic={watch.last_diagnostic} />
      )}

      {/* Events timeline */}
      {events && events.length > 0 && (
        <div className="rounded-lg border border-border bg-card">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-base font-semibold">Hændelser</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Tidspunkt
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Type
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">
                    Gammel pris
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">
                    Ny pris
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">
                    Ændring
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {events.map((event: PriceEvent) => (
                  <EventRow key={event.id} event={event} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-lg font-semibold">{children}</p>
    </div>
  );
}

function DiagnosticPanel({ diagnostic }: { diagnostic: WatchDiagnostic }) {
  const errType = diagnostic.error_type;
  const errorLabel = errType && errType in ERROR_TYPE_LABELS
    ? ERROR_TYPE_LABELS[errType].short
    : null;

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h2 className="text-base font-semibold">Seneste diagnostik</h2>
        <span className="text-xs text-muted-foreground tabular-nums">
          {new Date(diagnostic.checked_at).toLocaleString("da-DK")}
        </span>
      </div>
      <div className="p-5 space-y-3">
        {/* Error type banner */}
        {errorLabel && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3">
            <p className="text-sm font-medium text-destructive">{errorLabel}</p>
            {diagnostic.recommended_action && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {diagnostic.recommended_action}
              </p>
            )}
          </div>
        )}

        {/* Fetch metadata */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">HTTP-status</p>
            <p className="font-medium tabular-nums">
              {diagnostic.fetch.status_code || "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Svartid</p>
            <p className="font-medium tabular-nums">
              {diagnostic.fetch.response_time_ms > 0
                ? `${Math.round(diagnostic.fetch.response_time_ms)} ms`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">HTML-størrelse</p>
            <p className="font-medium tabular-nums">
              {diagnostic.fetch.html_length > 0
                ? `${(diagnostic.fetch.html_length / 1024).toFixed(1)} KB`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Provider</p>
            <p className="font-medium">{diagnostic.fetch.provider}</p>
          </div>
        </div>

        {/* Parsers tried */}
        {diagnostic.parse.extractors_tried.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Ekstraktorer forsøgt</p>
            <div className="flex flex-wrap gap-1">
              {diagnostic.parse.extractors_tried.map((name) => (
                <span
                  key={name}
                  className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-mono ${
                    diagnostic.parse.parser_used === name
                      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {name}
                  {diagnostic.parse.parser_used === name && (
                    <span className="ml-1">✓</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EventRow({ event }: { event: PriceEvent }) {
  const isDrop = (event.price_delta ?? 0) < 0;
  const isRise = (event.price_delta ?? 0) > 0;

  return (
    <tr className="hover:bg-muted/20 transition-colors">
      <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
        {formatRelative(event.occurred_at)}
      </td>
      <td className="px-4 py-2.5">
        {event.event_type === "price_change"
          ? "Prisændring"
          : event.event_type === "stock_change"
          ? "Lagerændring"
          : event.event_type}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums">
        {event.old_price != null ? formatPrice(event.old_price) : "—"}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums font-medium">
        {event.new_price != null ? formatPrice(event.new_price) : "—"}
      </td>
      <td
        className={`px-4 py-2.5 text-right tabular-nums font-medium ${
          isDrop ? "text-green-600" : isRise ? "text-red-500" : ""
        }`}
      >
        {event.price_delta != null
          ? `${isDrop ? "" : "+"}${formatPrice(event.price_delta)}`
          : "—"}
      </td>
    </tr>
  );
}
