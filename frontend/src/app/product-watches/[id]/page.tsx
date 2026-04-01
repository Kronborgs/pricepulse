"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/watches/status-badge";
import { PriceComparisonTable } from "@/components/watches/price-comparison-table";
import { formatPrice, formatRelative } from "@/lib/utils";
import { TimelineEvent } from "@/types";

// ─── Add source form schema ───────────────────────────────────────────────────
const addSourceSchema = z.object({
  url: z.string().url("Indtast en gyldig URL"),
  interval_override_min: z
    .string()
    .optional()
    .refine((v) => !v || /^\d+$/.test(v), "Skal være et tal")
    .transform((v) => (v ? parseInt(v) : undefined)),
  currency_hint: z.string().optional(),
});

type AddSourceValues = z.input<typeof addSourceSchema>;

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ProductWatchDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showAddSource, setShowAddSource] = useState(false);

  const { data: watch, isLoading } = useQuery({
    queryKey: ["product-watch", id],
    queryFn: () => api.productWatches.get(id),
    refetchInterval: 30_000,
  });

  const { data: timeline } = useQuery({
    queryKey: ["product-watch-timeline", id],
    queryFn: () => api.productWatches.timeline(id, 30),
    enabled: !!watch,
  });

  const qInvalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["product-watch", id] });

  const pauseMutation = useMutation({
    mutationFn: () => api.productWatches.pause(id),
    onSuccess: qInvalidate,
  });
  const resumeMutation = useMutation({
    mutationFn: () => api.productWatches.resume(id),
    onSuccess: qInvalidate,
  });

  const addSourceForm = useForm<AddSourceValues>({
    resolver: zodResolver(addSourceSchema),
    defaultValues: { url: "", interval_override_min: "" },
  });

  const addSourceMutation = useMutation({
    mutationFn: (values: AddSourceValues) =>
      api.productWatches.addSource(id, {
        url: values.url,
        interval_override_min: values.interval_override_min as number | undefined,
        currency_hint: (values.currency_hint as string) || undefined,
      }),
    onSuccess: () => {
      qInvalidate();
      addSourceForm.reset();
      setShowAddSource(false);
    },
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
        <p className="text-muted-foreground">ProductWatch ikke fundet</p>
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
              {watch.name ?? `Watch ${watch.id.slice(0, 8)}`}
            </h1>
            <StatusBadge status={watch.status} />
          </div>
          {watch.last_checked_at && (
            <div className="text-sm text-muted-foreground mt-0.5">
              Sidst tjekket {formatRelative(watch.last_checked_at)}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowAddSource(true)}
            className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Tilføj kilde
          </button>
          {watch.status === "paused" ? (
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
              disabled={pauseMutation.isPending || watch.status === "archived"}
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors disabled:opacity-50"
            >
              <Pause className="h-3.5 w-3.5" />
              Pause alle
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Bedste pris">
          {watch.last_best_price != null
            ? formatPrice(watch.last_best_price)
            : "—"}
        </StatCard>
        <StatCard label="Aktive kilder">
          {watch.sources.filter((s) => s.status === "active" || s.status === "pending").length}
        </StatCard>
        <StatCard label="Interval">
          {watch.default_interval_min} min
        </StatCard>
        <StatCard label="Oprettet">
          {formatRelative(watch.created_at)}
        </StatCard>
      </div>

      {/* Add source form */}
      {showAddSource && (
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <h2 className="text-base font-semibold">Tilføj ny kilde</h2>
          <form
            onSubmit={addSourceForm.handleSubmit((v) => addSourceMutation.mutate(v))}
            className="space-y-3"
          >
            <div>
              <label className="block text-sm font-medium mb-1">URL</label>
              <input
                type="url"
                {...addSourceForm.register("url")}
                placeholder="https://butik.dk/produkt/..."
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              {addSourceForm.formState.errors.url && (
                <p className="mt-1 text-xs text-destructive">
                  {addSourceForm.formState.errors.url.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Valuta{" "}
                <span className="font-normal text-muted-foreground">(valgfrit — til butikker uden auto-detektion)</span>
              </label>
              <select
                {...addSourceForm.register("currency_hint")}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Auto-detektér</option>
                <option value="DKK">DKK — Danske kroner</option>
                <option value="EUR">EUR — Euro</option>
                <option value="USD">USD — Amerikanske dollar</option>
                <option value="GBP">GBP — Britiske pund</option>
                <option value="SEK">SEK — Svenske kroner</option>
                <option value="NOK">NOK — Norske kroner</option>
                <option value="CHF">CHF — Schweiziske franc</option>
                <option value="PLN">PLN — Polske zloty</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Tilpasset interval (valgfrit)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  {...addSourceForm.register("interval_override_min")}
                  placeholder="Minutter"
                  min={5}
                  max={10080}
                  className="w-40 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <span className="text-sm text-muted-foreground">minutter</span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={addSourceMutation.isPending}
                className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm disabled:opacity-50"
              >
                {addSourceMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
                Tilføj kilde
              </button>
              <button
                type="button"
                onClick={() => { setShowAddSource(false); addSourceForm.reset(); }}
                className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
              >
                Annuller
              </button>
            </div>
            {addSourceMutation.isError && (
              <p className="text-xs text-destructive">
                {(addSourceMutation.error as Error).message}
              </p>
            )}
          </form>
        </div>
      )}

      {/* Price comparison table */}
      <PriceComparisonTable
        sources={watch.sources}
        bestSourceId={watch.last_best_source_id}
        watchId={id}
      />

      {/* Timeline */}
      {timeline && timeline.length > 0 && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-base font-semibold">Hændelseslog</h2>
          </div>
          <div className="divide-y divide-border">
            {timeline.map((ev) => (
              <TimelineRow key={ev.id} event={ev} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

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

const EVENT_TYPE_LABELS: Record<string, string> = {
  migrated_from_v1: "Migreret fra v1",
  source_added: "Kilde tilføjet",
  source_archived: "Kilde arkiveret",
  source_paused: "Kilde sat på pause",
  source_resumed: "Kilde genoptaget",
  watch_paused: "Watch sat på pause",
  watch_resumed: "Watch genoptaget",
  best_price_changed: "Bedste pris ændret",
  source_error: "Kilde fejl",
};

function TimelineRow({ event }: { event: TimelineEvent }) {
  const label = EVENT_TYPE_LABELS[event.event_type] ?? event.event_type;
  return (
    <div className="px-5 py-3 flex items-start gap-4">
      <span className="text-xs text-muted-foreground tabular-nums shrink-0 mt-0.5">
        {formatRelative(event.created_at)}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        {event.event_data && Object.keys(event.event_data).length > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {Object.entries(event.event_data)
              .filter(([, v]) => v != null)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ")}
          </p>
        )}
      </div>
    </div>
  );
}
