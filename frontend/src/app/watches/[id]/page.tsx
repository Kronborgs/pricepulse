"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  ExternalLink,
  Flag,
  Loader2,
  RefreshCw,
  Trash2,
  Wand2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { PriceChart } from "@/components/watches/price-chart";
import { StatusBadge } from "@/components/watches/status-badge";
import { ReportIssueDialog } from "@/components/watches/report-issue-dialog";
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
  const [showReport, setShowReport] = useState(false);

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

  const providerMutation = useMutation({
    mutationFn: (provider: string) => api.watches.update(id, { provider }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watch", id] }),
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
            onClick={() => setShowReport(true)}
            className="inline-flex items-center gap-1 rounded-md border border-amber-500/50 px-3 py-1.5 text-sm text-amber-400 hover:bg-amber-500/10 transition-colors"
            title="Rapportér problem med scraper"
          >
            <Flag className="h-3.5 w-3.5" />
            Rapportér
          </button>
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

      {/* Fetch method */}
      <div className="rounded-lg border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Hente-metode</h2>
          <span className="text-xs text-muted-foreground">
            Aktiv: <span className="font-medium text-foreground">
              {watch.provider === "playwright" ? "Browser/JS" : watch.provider === "curl_cffi" ? "Chrome-TLS" : "HTTP"}
            </span>
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Skift til Chrome-TLS hvis siden blokerer HTTP pga. TLS-fingerprinting. Brug Browser/JS hvis siden kræver JavaScript-rendering (kræver PLAYWRIGHT_ENABLED=true).
        </p>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => providerMutation.mutate("http")}
            disabled={providerMutation.isPending || watch.provider === "http"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              watch.provider === "http"
                ? "border-[#29ABE2] bg-[#29ABE2]/10 text-[#29ABE2] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            ⚡ HTTP (hurtig)
          </button>
          <button
            onClick={() => providerMutation.mutate("curl_cffi")}
            disabled={providerMutation.isPending || watch.provider === "curl_cffi"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              watch.provider === "curl_cffi"
                ? "border-[#F5A623] bg-[#F5A623]/10 text-[#F5A623] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            🔓 Chrome-TLS
          </button>
          <button
            onClick={() => providerMutation.mutate("playwright")}
            disabled={providerMutation.isPending || watch.provider === "playwright"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              watch.provider === "playwright"
                ? "border-[#8DC63F] bg-[#8DC63F]/10 text-[#8DC63F] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            🌐 Browser/JS
          </button>
        </div>
      </div>

      {/* Diagnostic panel — vis kun ved fejl eller hvis der er diagnostik */}
      {watch.last_diagnostic && (
        <DiagnosticPanel diagnostic={watch.last_diagnostic} watchId={id} />
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

    {showReport && (
      <ReportIssueDialog
        watchId={watch.id}
        watchTitle={watch.title ?? watch.url}
        onClose={() => setShowReport(false)}
      />
    )}
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

function DiagnosticPanel({ diagnostic, watchId }: { diagnostic: WatchDiagnostic; watchId: string }) {
  const errType = diagnostic.error_type;
  const errorLabel = errType && errType in ERROR_TYPE_LABELS
    ? ERROR_TYPE_LABELS[errType].short
    : null;
  const ollama = diagnostic.ollama_advice;
  const [applied, setApplied] = useState(false);
  const queryClient = useQueryClient();
  const applyMutation = useMutation({
    mutationFn: () =>
      api.watches.update(watchId, {
        scraper_config: {
          ...(ollama?.price_selector ? { price_selector: ollama.price_selector } : {}),
          ...(ollama?.stock_selector ? { stock_selector: ollama.stock_selector } : {}),
        },
      }),
    onSuccess: () => {
      setApplied(true);
      queryClient.invalidateQueries({ queryKey: ["watch", watchId] });
    },
  });

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

        {/* Ollama AI-rådgivning */}
        {ollama && (
          <div className="rounded-md border border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800 px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide">
                AI-analyse
              </span>
              {ollama.confidence > 0 && (
                <span className="text-xs text-blue-500 dark:text-blue-500">
                  {Math.round(ollama.confidence * 100)}% sikkerhed
                </span>
              )}
              {ollama.page_type && ollama.page_type !== "unknown" && (
                <span className="ml-auto text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 rounded px-1.5 py-0.5">
                  {ollama.page_type}
                </span>
              )}
            </div>

            {ollama.reasoning && (
              <p className="text-xs text-blue-800 dark:text-blue-300">{ollama.reasoning}</p>
            )}

            {ollama.recommended_action && (
              <p className="text-xs font-medium text-blue-900 dark:text-blue-200">
                ▶ {ollama.recommended_action}
              </p>
            )}

            {(ollama.price_selector || ollama.stock_selector) && (
              <div className="pt-1 space-y-1">
                {ollama.price_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-500 dark:text-blue-400 w-20 shrink-0">Pris:</span>
                    <code className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 rounded px-1.5 py-0.5 break-all">
                      {ollama.price_selector}
                    </code>
                  </div>
                )}
                {ollama.stock_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-500 dark:text-blue-400 w-20 shrink-0">Lager:</span>
                    <code className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 rounded px-1.5 py-0.5 break-all">
                      {ollama.stock_selector}
                    </code>
                  </div>
                )}
                <div className="pt-1">
                  <button
                    onClick={() => { setApplied(false); applyMutation.mutate(); }}
                    disabled={applyMutation.isPending}
                    className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                      applied
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 hover:bg-purple-200 dark:hover:bg-purple-900/50"
                    } disabled:opacity-50`}
                  >
                    {applied ? (
                      <><Check className="h-3 w-3" />Selectors gemt!</>
                    ) : (
                      <><Wand2 className="h-3 w-3" />Anvend AI-forslag</>
                    )}
                  </button>
                </div>
              </div>
            )}

            {(ollama.requires_js || ollama.likely_bot_protection) && (
              <div className="flex gap-2 pt-0.5">
                {ollama.requires_js && (
                  <span className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded px-1.5 py-0.5">
                    Kræver JavaScript
                  </span>
                )}
                {ollama.likely_bot_protection && (
                  <span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded px-1.5 py-0.5">
                    Bot-beskyttelse
                  </span>
                )}
              </div>
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
