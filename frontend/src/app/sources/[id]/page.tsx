"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Save,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/watches/status-badge";
import { LlmInsightPanel } from "@/components/watches/llm-insight-panel";
import { formatPrice, formatRelative } from "@/lib/utils";
import { SourceCheck, SourcePriceEvent } from "@/types";
import { ERROR_TYPE_LABELS } from "@/types";

export default function SourceDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const queryClient = useQueryClient();
  const [editingUrl, setEditingUrl] = useState(false);
  const [urlValue, setUrlValue] = useState("");
  const [editingInterval, setEditingInterval] = useState(false);
  const [intervalValue, setIntervalValue] = useState("");

  const { data: source, isLoading } = useQuery({
    queryKey: ["source", id],
    queryFn: () => api.sources.get(id),
    refetchInterval: 30_000,
  });

  const { data: checksData } = useQuery({
    queryKey: ["source-checks", id],
    queryFn: () => api.sources.checks(id, { limit: 50 }),
    enabled: !!source,
  });

  const { data: priceEvents } = useQuery({
    queryKey: ["source-price-events", id],
    queryFn: () => api.sources.priceEvents(id, 30),
    enabled: !!source,
  });

  const qInvalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["source", id] });
    queryClient.invalidateQueries({ queryKey: ["source-checks", id] });
  };

  const checkMutation = useMutation({
    mutationFn: () => api.sources.check(id),
    onSuccess: qInvalidate,
  });
  const pauseMutation = useMutation({
    mutationFn: () => api.sources.pause(id),
    onSuccess: qInvalidate,
  });
  const resumeMutation = useMutation({
    mutationFn: () => api.sources.resume(id),
    onSuccess: qInvalidate,
  });
  const updateMutation = useMutation({
    mutationFn: (data: { url?: string; interval_override_min?: number | null; provider?: string }) =>
      api.sources.update(id, data),
    onSuccess: () => {
      qInvalidate();
      setEditingUrl(false);
      setEditingInterval(false);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!source) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Kilde ikke fundet</p>
        <Link href="/watches" className="text-sm text-primary hover:underline">
          Tilbage til watches
        </Link>
      </div>
    );
  }

  const llmAdvice = source.last_diagnostic
    ? null
    : null; // Will be populated from LlmAnalysisResult when backend exposes it

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          href={`/product-watches/${source.watch_id}`}
          className="mt-1 rounded-md p-1 hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold truncate">{source.shop}</h1>
            <StatusBadge status={source.status} />
          </div>
          <div className="text-sm text-muted-foreground mt-0.5 truncate">{source.url}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          <a
            href={source.url}
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
            <RefreshCw className={`h-3.5 w-3.5 ${checkMutation.isPending ? "animate-spin" : ""}`} />
            Tjek nu
          </button>
          {source.status === "paused" ? (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors disabled:opacity-50 text-green-600"
            >
              <Play className="h-3.5 w-3.5" />
              Genoptag
            </button>
          ) : (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending || source.status === "archived"}
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors disabled:opacity-50"
            >
              <Pause className="h-3.5 w-3.5" />
              Pause
            </button>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Aktuel pris">
          {source.last_price != null
            ? formatPrice(source.last_price, source.last_currency)
            : "—"}
        </StatCard>
        <StatCard label="Lager">
          {source.last_stock_status === "in_stock"
            ? "På lager"
            : source.last_stock_status === "out_of_stock"
            ? "Udsolgt"
            : source.last_stock_status ?? "—"}
        </StatCard>
        <StatCard label="Fejl i træk">
          {source.consecutive_errors}
        </StatCard>
        <StatCard label="Interval">
          {source.interval_override_min != null
            ? `${source.interval_override_min} min (tilpasset)`
            : "Standard"}
        </StatCard>
      </div>

      {/* Edit URL */}
      <div className="rounded-lg border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">URL</h2>
          {!editingUrl && (
            <button
              onClick={() => { setUrlValue(source.url); setEditingUrl(true); }}
              className="text-xs text-primary hover:underline"
            >
              Redigér
            </button>
          )}
        </div>
        {editingUrl ? (
          <div className="flex gap-2">
            <input
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="https://..."
            />
            <button
              onClick={() => updateMutation.mutate({ url: urlValue })}
              disabled={updateMutation.isPending || !urlValue.trim()}
              className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              Gem
            </button>
            <button
              onClick={() => setEditingUrl(false)}
              className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
            >
              Annuller
            </button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground break-all">{source.url}</p>
        )}
        {source.previous_url && (
          <p className="text-xs text-muted-foreground">
            Tidligere: <span className="font-mono">{source.previous_url}</span>
          </p>
        )}
      </div>

      {/* Edit interval */}
      <div className="rounded-lg border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Tilpasset interval</h2>
          {!editingInterval && (
            <button
              onClick={() => {
                setIntervalValue(source.interval_override_min != null ? String(source.interval_override_min) : "");
                setEditingInterval(true);
              }}
              className="text-xs text-primary hover:underline"
            >
              {source.interval_override_min != null ? "Redigér" : "Tilpas"}
            </button>
          )}
        </div>
        {editingInterval ? (
          <div className="flex gap-2 items-center">
            <input
              type="number"
              value={intervalValue}
              onChange={(e) => setIntervalValue(e.target.value)}
              min={5}
              max={10080}
              placeholder="Minutter (tom = standard)"
              className="w-48 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <span className="text-sm text-muted-foreground">minutter</span>
            <button
              onClick={() =>
                updateMutation.mutate({
                  interval_override_min: intervalValue ? parseInt(intervalValue) : null,
                })
              }
              disabled={updateMutation.isPending}
              className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              Gem
            </button>
            <button
              onClick={() => setEditingInterval(false)}
              className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
            >
              Annuller
            </button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {source.interval_override_min != null
              ? `${source.interval_override_min} minutter`
              : "Bruger watch-standardinterval"}
          </p>
        )}
      </div>

      {/* Fetch method */}
      <div className="rounded-lg border border-border bg-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Hente-metode</h2>
          <span className="text-xs text-muted-foreground">
            Aktiv: <span className="font-medium text-foreground">
              {source.provider === "playwright" ? "Browser/JS" : source.provider === "curl_cffi" ? "Chrome-TLS" : "HTTP"}
            </span>
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Skift til Chrome-TLS hvis siden blokerer HTTP pga. TLS-fingerprinting. Brug Browser/JS hvis siden kræver JavaScript-rendering (kræver PLAYWRIGHT_ENABLED=true).
        </p>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => updateMutation.mutate({ provider: "http" })}
            disabled={updateMutation.isPending || source.provider === "http"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              source.provider === "http"
                ? "border-[#29ABE2] bg-[#29ABE2]/10 text-[#29ABE2] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            ⚡ HTTP (hurtig)
          </button>
          <button
            onClick={() => updateMutation.mutate({ provider: "curl_cffi" })}
            disabled={updateMutation.isPending || source.provider === "curl_cffi"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              source.provider === "curl_cffi"
                ? "border-[#F5A623] bg-[#F5A623]/10 text-[#F5A623] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            🔓 Chrome-TLS
          </button>
          <button
            onClick={() => updateMutation.mutate({ provider: "playwright" })}
            disabled={updateMutation.isPending || source.provider === "playwright"}
            className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
              source.provider === "playwright"
                ? "border-[#8DC63F] bg-[#8DC63F]/10 text-[#8DC63F] font-medium"
                : "border-border hover:bg-muted disabled:opacity-50"
            }`}
          >
            🌐 Browser/JS
          </button>
        </div>
      </div>

      {/* Diagnostic */}
      {source.last_diagnostic && (
        <DiagnosticPanel diagnostic={source.last_diagnostic} />
      )}

      {/* AI insight */}
      <LlmInsightPanel sourceId={id} existing={llmAdvice} />

      {/* Check history */}
      {checksData && checksData.items.length > 0 && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-base font-semibold">Tjek-historik</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Tidspunkt</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Pris</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground hidden sm:table-cell">Lager</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground hidden md:table-cell">Svartid</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {checksData.items.map((check) => (
                  <CheckRow key={check.id} check={check} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Price events */}
      {priceEvents && priceEvents.length > 0 && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-base font-semibold">Prisændringer</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Tidspunkt</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Type</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Gammel pris</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Ny pris</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {priceEvents.map((ev) => (
                  <PriceEventRow key={ev.id} event={ev} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-lg font-semibold">{children}</p>
    </div>
  );
}

function DiagnosticPanel({ diagnostic }: { diagnostic: import("@/types").WatchDiagnostic }) {
  const errType = diagnostic.error_type;
  const errorLabel = errType && errType in ERROR_TYPE_LABELS ? ERROR_TYPE_LABELS[errType].short : null;
  const ollama = diagnostic.ollama_advice;
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h2 className="text-base font-semibold">Seneste diagnostik</h2>
        <span className="text-xs text-muted-foreground tabular-nums">
          {new Date(diagnostic.checked_at).toLocaleString("da-DK")}
        </span>
      </div>
      <div className="p-5 space-y-3">
        {errorLabel && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3">
            <p className="text-sm font-medium text-destructive">{errorLabel}</p>
            {diagnostic.recommended_action && (
              <p className="text-xs text-muted-foreground mt-0.5">{diagnostic.recommended_action}</p>
            )}
          </div>
        )}
        {/* Ollama AI-rådgivning */}
        {ollama && (
          <div className="rounded-md border border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800 px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide">AI-analyse</span>
              {ollama.confidence > 0 && (
                <span className="text-xs text-blue-500">{Math.round(ollama.confidence * 100)}% sikkerhed</span>
              )}
              {ollama.page_type && ollama.page_type !== "unknown" && (
                <span className="ml-auto text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 rounded px-1.5 py-0.5">{ollama.page_type}</span>
              )}
            </div>
            {ollama.reasoning && <p className="text-xs text-blue-800 dark:text-blue-300">{ollama.reasoning}</p>}
            {ollama.recommended_action && (
              <p className="text-xs font-medium text-blue-900 dark:text-blue-200">▶ {ollama.recommended_action}</p>
            )}
            {(ollama.price_selector || ollama.stock_selector) && (
              <div className="pt-1 space-y-1">
                {ollama.price_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-500 w-20 shrink-0">Pris:</span>
                    <code className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 rounded px-1.5 py-0.5 break-all">{ollama.price_selector}</code>
                  </div>
                )}
                {ollama.stock_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-500 w-20 shrink-0">Lager:</span>
                    <code className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 rounded px-1.5 py-0.5 break-all">{ollama.stock_selector}</code>
                  </div>
                )}
              </div>
            )}
            {(ollama.requires_js || ollama.likely_bot_protection) && (
              <div className="flex gap-2 pt-0.5">
                {ollama.requires_js && <span className="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded px-1.5 py-0.5">Kræver JavaScript</span>}
                {ollama.likely_bot_protection && <span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded px-1.5 py-0.5">Bot-beskyttelse</span>}
              </div>
            )}
          </div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">HTTP-status</p>
            <p className="font-medium tabular-nums">{diagnostic.fetch.status_code || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Svartid</p>
            <p className="font-medium tabular-nums">
              {diagnostic.fetch.response_time_ms > 0 ? `${Math.round(diagnostic.fetch.response_time_ms)} ms` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">HTML-størrelse</p>
            <p className="font-medium tabular-nums">
              {diagnostic.fetch.html_length > 0 ? `${(diagnostic.fetch.html_length / 1024).toFixed(1)} KB` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Provider</p>
            <p className="font-medium">{diagnostic.fetch.provider}</p>
          </div>
        </div>
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
                  {diagnostic.parse.parser_used === name && <span className="ml-1">✓</span>}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const CHANGE_TYPE_LABELS: Record<import("@/types").ChangeType, { label: string; class: string }> = {
  initial:       { label: "Første pris",   class: "text-muted-foreground" },
  increase:      { label: "Prisstigning",  class: "text-red-500" },
  decrease:      { label: "Prisfald",      class: "text-green-600" },
  unavailable:   { label: "Ikke tilgæng.", class: "text-orange-500" },
  back_in_stock: { label: "Tilbage",       class: "text-blue-500" },
};

function PriceEventRow({ event }: { event: SourcePriceEvent }) {
  const ct = CHANGE_TYPE_LABELS[event.change_type] ?? { label: event.change_type, class: "" };
  return (
    <tr className="hover:bg-muted/20 transition-colors">
      <td className="px-4 py-2.5 tabular-nums text-muted-foreground">{formatRelative(event.created_at)}</td>
      <td className={`px-4 py-2.5 font-medium ${ct.class}`}>{ct.label}</td>
      <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
        {event.old_price != null ? formatPrice(event.old_price) : "—"}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums font-medium">
        {event.new_price != null ? formatPrice(event.new_price) : "—"}
      </td>
    </tr>
  );
}

function CheckRow({ check }: { check: SourceCheck }) {
  return (
    <tr className="hover:bg-muted/20 transition-colors">
      <td className="px-4 py-2.5 tabular-nums text-muted-foreground">{formatRelative(check.checked_at)}</td>
      <td className="px-4 py-2.5 text-right tabular-nums font-medium">
        {check.price != null ? formatPrice(check.price, check.currency) : "—"}
      </td>
      <td className="px-4 py-2.5 hidden sm:table-cell text-muted-foreground">
        {check.stock_status === "in_stock" ? "På lager" : check.stock_status === "out_of_stock" ? "Udsolgt" : check.stock_status ?? "—"}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums hidden md:table-cell text-muted-foreground">
        {check.response_time_ms != null ? `${Math.round(check.response_time_ms)} ms` : "—"}
      </td>
      <td className="px-4 py-2.5">
        {check.success ? (
          <span className="text-xs text-green-600">✓ OK</span>
        ) : (
          <span className="text-xs text-red-500">
            {check.error_type
              ? ERROR_TYPE_LABELS[check.error_type]?.short ?? check.error_type
              : "Fejl"}
          </span>
        )}
      </td>
    </tr>
  );
}
