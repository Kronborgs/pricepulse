"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Check, CheckCircle2, Loader2, RefreshCw, X, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Shop } from "@/types";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Indstillinger</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Konfigurer butikker og systemindstillinger
        </p>
      </div>

      <HealthCard />
      <OllamaSection />
      <ShopsSection />
    </div>
  );
}

function HealthCard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      return res.json() as Promise<{ status: string; version: string }>;
    },
    retry: false,
    refetchInterval: 30_000,
  });

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-base font-semibold mb-4">Systemstatus</h2>
      <div className="flex items-start gap-2">
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mt-0.5" />
            <span className="text-sm text-muted-foreground">Tjekker...</span>
          </>
        ) : error ? (
          <>
            <XCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-sm text-destructive font-medium">Backend fejlede</span>
              <p className="text-xs text-muted-foreground mt-0.5 font-mono break-all">
                {error instanceof Error ? error.message : String(error)}
              </p>
            </div>
          </>
        ) : (
          <>
            <CheckCircle2 className="h-4 w-4 text-[#8DC63F] flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-sm font-medium">Backend kører</span>
              <p className="text-xs text-muted-foreground mt-0.5">
                {data?.version ? `v${data.version}` : "OK"}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Ollama sektion ───────────────────────────────────────────────────────────

function OllamaSection() {
  const qc = useQueryClient();
  const [editHost, setEditHost] = useState(false);
  const [hostValue, setHostValue] = useState("");
  const [editModels, setEditModels] = useState(false);
  const [parserModel, setParserModel] = useState("");
  const [normalizeModel, setNormalizeModel] = useState("");
  const [embedModel, setEmbedModel] = useState("");

  const { data: status, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["ollama-status"],
    queryFn: () => api.ollama.status(),
    refetchInterval: 60_000,
  });

  const patchMutation = useMutation({
    mutationFn: api.ollama.updateConfig,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ollama-status"] });
      setEditHost(false);
      setEditModels(false);
    },
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Indlæser Ollama-status…</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card divide-y divide-border">
      {/* Header + toggle */}
      <div className="px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-purple-500" />
          <div>
            <h2 className="text-base font-semibold">Ollama AI</h2>
            <p className="text-xs text-muted-foreground">
              Lokal sprogmodel til parser-diagnostik og produktnormalisering
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-1.5 rounded hover:bg-white/8 text-muted-foreground transition-colors"
            title="Genindlæs status"
          >
            <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
          </button>
          <button
            onClick={() => patchMutation.mutate({ enabled: !status?.enabled })}
            disabled={patchMutation.isPending}
            className={cn(
              "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
              status?.enabled ? "bg-green-500" : "bg-muted-foreground/30"
            )}
            title={status?.enabled ? "Deaktivér Ollama" : "Aktivér Ollama"}
          >
            <span className={cn(
              "inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
              status?.enabled ? "translate-x-6" : "translate-x-1"
            )} />
          </button>
          <span className="text-sm font-medium w-20">
            {status?.enabled ? "Aktiveret" : "Deaktiveret"}
          </span>
        </div>
      </div>

      {/* Connection status */}
      <div className="px-6 py-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Forbindelsesstatus
        </p>
        <div className="flex items-center gap-2">
          {status?.available ? (
            <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
          ) : (
            <X className="h-4 w-4 text-red-500 flex-shrink-0" />
          )}
          <span className="text-sm font-medium">
            {status?.available ? "Forbundet" : status?.enabled ? "Ikke tilgængelig" : "Deaktiveret"}
          </span>
        </div>
        {status?.available && status.models.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {status.models.map((m) => (
              <span key={m} className="inline-flex items-center rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400 px-2.5 py-0.5 text-xs font-mono">
                {m}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Host */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Host</p>
          {!editHost && (
            <button onClick={() => { setHostValue(status?.host ?? ""); setEditHost(true); }} className="text-xs text-primary hover:underline">
              Redigér
            </button>
          )}
        </div>
        {editHost ? (
          <div className="flex gap-2 mt-2">
            <input
              type="url"
              value={hostValue}
              onChange={(e) => setHostValue(e.target.value)}
              placeholder="http://10.10.80.10:11434"
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button onClick={() => patchMutation.mutate({ host: hostValue })} disabled={patchMutation.isPending || !hostValue.trim()} className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">Gem</button>
            <button onClick={() => setEditHost(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">Annuller</button>
          </div>
        ) : (
          <p className="text-sm font-mono mt-1">{status?.host}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1.5">
          RAM-ændring kun — sæt <code className="bg-muted rounded px-1">OLLAMA_HOST</code> i env-filen for permanent ændring.
        </p>
      </div>

      {/* Models */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Modeller</p>
          {!editModels && (
            <button onClick={() => { setParserModel(status?.parser_model ?? ""); setNormalizeModel(status?.normalize_model ?? ""); setEmbedModel(status?.embed_model ?? ""); setEditModels(true); }} className="text-xs text-primary hover:underline">
              Redigér
            </button>
          )}
        </div>
        {editModels ? (
          <div className="space-y-3">
            {([
              ["Parser", parserModel, setParserModel],
              ["Normalisering", normalizeModel, setNormalizeModel],
              ["Embedding", embedModel, setEmbedModel],
            ] as [string, string, (v: string) => void][]).map(([label, value, setter]) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-24 shrink-0">{label}</span>
                <input type="text" value={value} onChange={(e) => setter(e.target.value)} className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <button onClick={() => patchMutation.mutate({ parser_model: parserModel || undefined, normalize_model: normalizeModel || undefined, embed_model: embedModel || undefined })} disabled={patchMutation.isPending} className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">Gem</button>
              <button onClick={() => setEditModels(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">Annuller</button>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {([["Parser", status?.parser_model], ["Normalisering", status?.normalize_model], ["Embedding", status?.embed_model]] as [string, string | undefined][]).map(([label, value]) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-24 shrink-0">{label}</span>
                <span className="text-sm font-mono">{value ?? "—"}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {patchMutation.isError && (
        <div className="px-6 py-3 bg-destructive/10 text-destructive text-xs">
          {(patchMutation.error as Error).message}
        </div>
      )}
    </div>
  );
}

function ShopsSection() {
  const queryClient = useQueryClient();

  const { data: shops, isLoading } = useQuery({
    queryKey: ["shops"],
    queryFn: api.shops.list,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.shops.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shops"] }),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-base font-semibold mb-4">Butikker</h2>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const shopList: Shop[] = shops ?? [];

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-semibold">Butikker</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Aktiver eller deaktiver butikker der scrapes
        </p>
      </div>
      <div className="divide-y divide-border">
        {shopList.map((shop) => (
          <ShopRow
            key={shop.id}
            shop={shop}
            onToggle={(is_active) =>
              toggleMutation.mutate({ id: shop.id, is_active })
            }
            isPending={toggleMutation.isPending}
          />
        ))}
        {shopList.length === 0 && (
          <p className="px-5 py-6 text-sm text-muted-foreground">
            Ingen butikker. Kør seed-scriptet for at tilføje dem.
          </p>
        )}
      </div>
    </div>
  );
}

function ShopRow({
  shop,
  onToggle,
  isPending,
}: {
  shop: Shop;
  onToggle: (is_active: boolean) => void;
  isPending: boolean;
}) {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="flex-1 min-w-0">
        <p className="font-medium">{shop.name}</p>
        <p className="text-xs text-muted-foreground">
          {shop.domain} · {shop.default_provider} ·{" "}
          {shop.watch_count} watch{shop.watch_count !== 1 ? "es" : ""}
        </p>
      </div>

      <button
        onClick={() => onToggle(!shop.is_active)}
        disabled={isPending}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 ${
          shop.is_active ? "bg-primary" : "bg-muted"
        }`}
        aria-label={shop.is_active ? "Deaktiver butik" : "Aktiver butik"}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
            shop.is_active ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
