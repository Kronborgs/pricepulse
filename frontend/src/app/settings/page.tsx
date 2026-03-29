"use client";

import { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Check, CheckCircle2, Download, HardDrive, Info, KeyRound, Loader2, RefreshCw, RotateCcw, Trash2, Upload, X, XCircle } from "lucide-react";
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
      <BackupSection />
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

function BackupSection() {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [editConfig, setEditConfig] = useState(false);
  const [cfgEnabled, setCfgEnabled] = useState(false);
  const [cfgHours, setCfgHours] = useState(24);
  const [cfgKeep, setCfgKeep] = useState(7);

  // Restore confirm dialog state
  const [restoreTarget, setRestoreTarget] = useState<string | null>(null); // filename or "upload"
  const [importUsers, setImportUsers] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [restoreResult, setRestoreResult] = useState<Record<string, number> | null>(null);

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ["backup-config"],
    queryFn: api.backup.getConfig,
  });

  const { data: backups, isLoading: listLoading, refetch: refetchList, isRefetching } = useQuery({
    queryKey: ["backup-list"],
    queryFn: api.backup.list,
  });

  const runMutation = useMutation({
    mutationFn: api.backup.run,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backup-list"] }),
  });

  const configMutation = useMutation({
    mutationFn: api.backup.updateConfig,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["backup-config"] });
      setEditConfig(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.backup.deleteBackup,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backup-list"] }),
  });

  const restoreMutation = useMutation({
    mutationFn: ({ filename, importUsers }: { filename: string; importUsers: boolean }) =>
      filename === "__upload__" && uploadFile
        ? api.backup.uploadRestore(uploadFile, importUsers)
        : api.backup.restore(filename, importUsers),
    onSuccess: (data) => {
      setRestoreResult(data.stats);
      setRestoreTarget(null);
      setUploadFile(null);
    },
  });

  function openEdit() {
    setCfgEnabled(config?.enabled ?? false);
    setCfgHours(config?.interval_hours ?? 24);
    setCfgKeep(config?.keep_count ?? 7);
    setEditConfig(true);
  }

  function formatBytes(n: number): string {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1024 / 1024).toFixed(1)} MB`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString("da-DK", { dateStyle: "short", timeStyle: "short" });
  }

  const STAT_LABELS: Record<string, string> = {
    products: "Produkter",
    v1_watches: "Watches (v1)",
    v1_price_history: "Prishistorik (v1)",
    v2_watches: "Watches (v2)",
    v2_watch_sources: "Watch Sources",
    v2_price_events: "Prisændringer (v2)",
    users: "Brugere",
    smtp_restored: "SMTP-opsætning",
  };

  return (
    <div className="rounded-lg border border-border bg-card divide-y divide-border">
      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <HardDrive className="h-5 w-5 text-blue-500" />
          <div>
            <h2 className="text-base font-semibold">Backup</h2>
            <p className="text-xs text-muted-foreground">
              Gemmes i <code className="bg-muted rounded px-1">/app/data/backup</code> · host: <code className="bg-muted rounded px-1">/mnt/user/appdata/pricepulse/backup</code>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => refetchList()}
            disabled={isRefetching}
            className="p-1.5 rounded hover:bg-white/8 text-muted-foreground transition-colors"
            title="Genindlæs liste"
          >
            <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
          </button>
          {/* Upload & restore (frisk install) */}
          <button
            onClick={() => {
              setRestoreTarget("__upload__");
              setImportUsers(true);
              setUploadFile(null);
              setRestoreResult(null);
            }}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <Upload className="h-3.5 w-3.5" />
            Importer backup-fil
          </button>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {runMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <HardDrive className="h-3.5 w-3.5" />}
            Kør backup nu
          </button>
        </div>
      </div>

      {runMutation.isSuccess && (
        <div className="px-6 py-2 bg-green-500/10 text-green-600 dark:text-green-400 text-xs flex items-center gap-1.5">
          <Check className="h-3.5 w-3.5" />
          Backup oprettet: {runMutation.data?.filename}
        </div>
      )}
      {runMutation.isError && (
        <div className="px-6 py-2 bg-destructive/10 text-destructive text-xs">
          {(runMutation.error as Error).message}
        </div>
      )}

      {/* Restore result */}
      {restoreResult && (
        <div className="px-6 py-3 bg-green-500/10 border-b border-border">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-green-600 dark:text-green-400 flex items-center gap-1.5">
              <Check className="h-4 w-4" /> Restore gennemført
            </p>
            <button onClick={() => setRestoreResult(null)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1">
            {Object.entries(restoreResult).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{STAT_LABELS[k] ?? k}</span>
                <span className="font-mono font-medium">{v}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
            ⚠ SMTP-indstillinger gendannes (deaktiverede) — genindtast <strong>kodeordet</strong> under Mail-indstillinger for at aktivere.
          </p>
        </div>
      )}

      {/* Restore confirm modal (fra liste) */}
      {restoreTarget && restoreTarget !== "__upload__" && (
        <div className="px-6 py-4 bg-amber-500/10 space-y-3">
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Gendan fra: <span className="font-mono">{restoreTarget}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Data UPSERTS — eksisterende poster opdateres, manglende tilføjes. Intet slettes.
          </p>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={importUsers} onChange={(e) => setImportUsers(e.target.checked)} className="rounded" />
            Importer brugere (inkl. adgangskoder fra backup)
          </label>
          {restoreMutation.isError && (
            <p className="text-xs text-destructive">{(restoreMutation.error as Error).message}</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => restoreMutation.mutate({ filename: restoreTarget, importUsers })}
              disabled={restoreMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-amber-600 text-white px-3 py-1.5 text-sm disabled:opacity-50"
            >
              {restoreMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
              Gendan
            </button>
            <button onClick={() => setRestoreTarget(null)} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
              Annuller
            </button>
          </div>
        </div>
      )}

      {/* Upload & restore modal */}
      {restoreTarget === "__upload__" && (
        <div className="px-6 py-4 bg-blue-500/10 space-y-3">
          <p className="text-sm font-semibold text-blue-700 dark:text-blue-400 flex items-center gap-2">
            <Upload className="h-4 w-4" /> Importer backup-fil
          </p>
          <p className="text-xs text-muted-foreground">
            Upload en tidligere downloadet <code className="bg-muted rounded px-1">.json.gz</code> backup-fil. Bruges til genoprettelse på ny server.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json.gz,.gz"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            className="block text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:py-1 file:text-sm file:cursor-pointer"
          />
          {uploadFile && (
            <p className="text-xs text-muted-foreground">Valgt: <span className="font-mono">{uploadFile.name}</span> ({formatBytes(uploadFile.size)})</p>
          )}
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={importUsers} onChange={(e) => setImportUsers(e.target.checked)} className="rounded" />
            Importer brugere (inkl. adgangskoder fra backup)
          </label>
          {restoreMutation.isError && (
            <p className="text-xs text-destructive">{(restoreMutation.error as Error).message}</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => uploadFile && restoreMutation.mutate({ filename: "__upload__", importUsers })}
              disabled={!uploadFile || restoreMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 text-white px-3 py-1.5 text-sm disabled:opacity-50"
            >
              {restoreMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
              Importer og gendan
            </button>
            <button onClick={() => { setRestoreTarget(null); setUploadFile(null); }} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
              Annuller
            </button>
          </div>
        </div>
      )}

      {/* Config */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Automatisk backup</p>
          {!editConfig && (
            <button onClick={openEdit} className="text-xs text-primary hover:underline">Redigér</button>
          )}
        </div>
        {configLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : editConfig ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">Aktiveret</span>
              <button
                onClick={() => setCfgEnabled((v) => !v)}
                className={cn("relative inline-flex h-6 w-11 items-center rounded-full transition-colors", cfgEnabled ? "bg-green-500" : "bg-muted-foreground/30")}
              >
                <span className={cn("inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform", cfgEnabled ? "translate-x-6" : "translate-x-1")} />
              </button>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">Interval (timer)</span>
              <input type="number" min={1} max={8760} value={cfgHours} onChange={(e) => setCfgHours(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">Behold antal</span>
              <input type="number" min={1} max={365} value={cfgKeep} onChange={(e) => setCfgKeep(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={() => configMutation.mutate({ enabled: cfgEnabled, interval_hours: cfgHours, keep_count: cfgKeep })}
                disabled={configMutation.isPending}
                className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">Gem</button>
              <button onClick={() => setEditConfig(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">Annuller</button>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {([
              ["Status", config?.enabled ? "Aktiveret" : "Deaktiveret"],
              ["Interval", `Hver ${config?.interval_hours ?? 24} timer`],
              ["Behold", `${config?.keep_count ?? 7} seneste`],
            ] as [string, string][]).map(([label, value]) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-32 shrink-0">{label}</span>
                <span className="text-sm">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SMTP note */}
      <div className="px-6 py-3 flex items-start gap-3 bg-muted/30">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-slate-800 ring-1 ring-slate-700 mt-0.5">
          <KeyRound className="h-3.5 w-3.5 text-slate-400" />
        </div>
        <div className="space-y-0.5">
          <p className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Info className="h-3 w-3 text-slate-500" />
            SMTP-kodeord gemmes ikke i backup
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Af sikkerhedsmæssige årsager inkluderer backuppen <strong className="text-slate-400">ikke</strong> dit SMTP-kodeord.
            Øvrige SMTP-indstillinger (server, port, afsender m.m.) er gemt, men
            genoplæses som <em>deaktiverede</em> — du skal genindtaste kodeordet
            under <strong className="text-slate-400">Admin → SMTP</strong> for at
            aktivere e-mail notifikationer igen.
          </p>
        </div>
      </div>

      {/* Backup list */}
      <div className="px-6 py-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Gemte backups</p>
        {listLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : !backups || backups.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ingen backups endnu — klik "Kør backup nu".</p>
        ) : (
          <div className="divide-y divide-border rounded-md border border-border overflow-hidden">
            {backups.map((b) => (
              <div key={b.filename} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono truncate">{b.filename}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{formatDate(b.created_at)} · {formatBytes(b.size_bytes)}</p>
                </div>
                <button
                  onClick={() => { setRestoreTarget(b.filename); setImportUsers(true); setRestoreResult(null); }}
                  className="p-1.5 rounded hover:bg-amber-500/10 text-muted-foreground hover:text-amber-500 transition-colors"
                  title="Gendan fra denne backup"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
                <a
                  href={api.backup.downloadUrl(b.filename)}
                  download={b.filename}
                  className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Download backup"
                >
                  <Download className="h-4 w-4" />
                </a>
                <button
                  onClick={() => deleteMutation.mutate(b.filename)}
                  disabled={deleteMutation.isPending}
                  className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
                  title="Slet backup"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
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
