"use client";

import { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Check, CheckCircle2, Download, HardDrive, Info, KeyRound, Loader2, Lock, RefreshCw, RotateCcw, Trash2, Upload, X, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Shop } from "@/types";
import { cn } from "@/lib/utils";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useI18n } from "@/lib/i18n";

export default function SettingsPage() {
  const { t } = useI18n();
  const { data: me } = useCurrentUser();
  const readonly = me?.role === "user";
  const superuserReadonly = me?.role === "user" || me?.role === "superuser";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("settings_title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("settings_subtitle")}
        </p>
      </div>

      <HealthCard />
      <OllamaSection readonly={superuserReadonly} />
      <BackupSection readonly={superuserReadonly} />
      <ShopsSection readonly={superuserReadonly} />
    </div>
  );
}

function HealthCard() {
  const { t } = useI18n();
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
      <h2 className="text-base font-semibold mb-4">{t("settings_system_status")}</h2>
      <div className="flex items-start gap-2">
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mt-0.5" />
            <span className="text-sm text-muted-foreground">{t("settings_checking")}</span>
          </>
        ) : error ? (
          <>
            <XCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-sm text-destructive font-medium">{t("settings_backend_error")}</span>
              <p className="text-xs text-muted-foreground mt-0.5 font-mono break-all">
                {error instanceof Error ? error.message : String(error)}
              </p>
            </div>
          </>
        ) : (
          <>
            <CheckCircle2 className="h-4 w-4 text-[#8DC63F] flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-sm font-medium">{t("settings_backend_ok")}</span>
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

function OllamaSection({ readonly }: { readonly?: boolean }) {
  const { t } = useI18n();
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
        <span className="text-sm text-muted-foreground">{t("settings_checking")}</span>
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
            <h2 className="text-base font-semibold">{t("settings_ollama")}</h2>
            <p className="text-xs text-muted-foreground">
              {t("settings_ollama_desc")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-1.5 rounded hover:bg-white/8 text-muted-foreground transition-colors"
            title={t("settings_reload_status")}>
          >
            <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
          </button>
          {readonly ? (
            <span title={t("settings_read_only")}><Lock className="h-4 w-4 text-muted-foreground" /></span>
          ) : (
            <button
              onClick={() => patchMutation.mutate({ enabled: !status?.enabled })}
              disabled={patchMutation.isPending}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                status?.enabled ? "bg-green-500" : "bg-muted-foreground/30"
              )}
              title={status?.enabled ? t("settings_disabled") + " Ollama" : t("settings_enabled") + " Ollama"}
            >
              <span className={cn(
                "inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
                status?.enabled ? "translate-x-6" : "translate-x-1"
              )} />
            </button>
          )}
          {readonly ? (
            <span className={cn("text-sm font-medium w-20 text-muted-foreground", !status?.enabled && "opacity-60")}>
            {status?.enabled ? t("settings_enabled") : t("settings_disabled")}
            </span>
          ) : (
            <span className="text-sm font-medium w-20">
              {status?.enabled ? t("settings_enabled") : t("settings_disabled")}
            </span>
          )}
        </div>
      </div>

      {/* Connection status */}
      <div className="px-6 py-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
          {t("settings_connection_status")}
        </p>
        <div className="flex items-center gap-2">
          {status?.available ? (
            <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
          ) : (
            <X className="h-4 w-4 text-red-500 flex-shrink-0" />
          )}
          <span className="text-sm font-medium">
            {status?.available ? t("settings_connected") : status?.enabled ? t("settings_unavailable") : t("settings_disabled")}
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
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t("settings_host")}</p>
          {!editHost && !readonly && (
            <button onClick={() => { setHostValue(status?.host ?? ""); setEditHost(true); }} className="text-xs text-primary hover:underline">
              {t("settings_edit")}
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
            <button onClick={() => patchMutation.mutate({ host: hostValue })} disabled={patchMutation.isPending || !hostValue.trim()} className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">{t("settings_save")}</button>
            <button onClick={() => setEditHost(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">{t("settings_cancel")}</button>
          </div>
        ) : (
          <p className="text-sm font-mono mt-1">{status?.host}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1.5">
          RAM change only — set <code className="bg-muted rounded px-1">OLLAMA_HOST</code> in the env file for permanent change.
        </p>
      </div>

      {/* Models */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t("settings_models")}</p>
          {!editModels && !readonly && (
            <button onClick={() => { setParserModel(status?.parser_model ?? ""); setNormalizeModel(status?.normalize_model ?? ""); setEmbedModel(status?.embed_model ?? ""); setEditModels(true); }} className="text-xs text-primary hover:underline">
              {t("settings_edit")}
            </button>
          )}
        </div>
        {editModels ? (
          <div className="space-y-3">
            {([
              [t("settings_parser"), parserModel, setParserModel],
              [t("settings_normalisation"), normalizeModel, setNormalizeModel],
              [t("settings_embedding"), embedModel, setEmbedModel],
            ] as [string, string, (v: string) => void][]).map(([label, value, setter]) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-24 shrink-0">{label}</span>
                <input type="text" value={value} onChange={(e) => setter(e.target.value)} className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <button onClick={() => patchMutation.mutate({ parser_model: parserModel || undefined, normalize_model: normalizeModel || undefined, embed_model: embedModel || undefined })} disabled={patchMutation.isPending} className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">{t("settings_save")}</button>
              <button onClick={() => setEditModels(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">{t("settings_cancel")}</button>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {([          [t("settings_parser"), status?.parser_model], [t("settings_normalisation"), status?.normalize_model], [t("settings_embedding"), status?.embed_model]] as [string, string | undefined][]).map(([label, value]) => (
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

function BackupSection({ readonly }: { readonly?: boolean }) {
  const { t } = useI18n();
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
    return new Date(iso).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" });
  }

  const STAT_LABELS: Record<string, string> = {
    products: t("products_title"),
    v1_watches: "Watches (v1)",
    v1_price_history: "Price history (v1)",
    v2_watches: "Watches (v2)",
    v2_watch_sources: "Watch Sources",
    v2_price_events: "Price events (v2)",
    users: t("admin_users_title"),
    smtp_restored: "SMTP setup",
  };

  return (
    <div className={cn("rounded-lg border border-border bg-card divide-y divide-border", readonly && "opacity-60 pointer-events-none select-none")}>
      {readonly && (
        <div className="px-5 py-2.5 flex items-center gap-2 bg-slate-800/60 rounded-t-lg border-b border-border">
          <Lock className="h-3.5 w-3.5 text-slate-400 shrink-0" />
          <span className="text-xs text-slate-400">Only administrators can change backup settings</span>
        </div>
      )}
      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <HardDrive className="h-5 w-5 text-blue-500" />
          <div>
            <h2 className="text-base font-semibold">{t("settings_backup")}</h2>
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
            title="Reload list">
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
            {t("settings_import_backup")}
          </button>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {runMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <HardDrive className="h-3.5 w-3.5" />}
            {t("settings_run_backup")}
          </button>
        </div>
      </div>

      {runMutation.isSuccess && (
        <div className="px-6 py-2 bg-green-500/10 text-green-600 dark:text-green-400 text-xs flex items-center gap-1.5">
          <Check className="h-3.5 w-3.5" />
          Backup created: {runMutation.data?.filename}
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
              <Check className="h-4 w-4" /> {t("settings_restore_done")}
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
            ⚠ SMTP settings are restored (disabled) — re-enter the <strong>password</strong> under Mail settings to activate.
          </p>
        </div>
      )}

      {/* Restore confirm modal (fra liste) */}
      {restoreTarget && restoreTarget !== "__upload__" && (
        <div className="px-6 py-4 bg-amber-500/10 space-y-3">
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Restore from: <span className="font-mono">{restoreTarget}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Data UPSERTS — existing records are updated, missing ones added. Nothing is deleted.
          </p>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={importUsers} onChange={(e) => setImportUsers(e.target.checked)} className="rounded" />
            Import users (incl. passwords from backup)
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
              {t("settings_restore")}
            </button>
            <button onClick={() => setRestoreTarget(null)} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
              {t("settings_cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Upload & restore modal */}
      {restoreTarget === "__upload__" && (
        <div className="px-6 py-4 bg-blue-500/10 space-y-3">
          <p className="text-sm font-semibold text-blue-700 dark:text-blue-400 flex items-center gap-2">
            <Upload className="h-4 w-4" /> {t("settings_import_backup")}
          </p>
          <p className="text-xs text-muted-foreground">
            Upload a previously downloaded <code className="bg-muted rounded px-1">.json.gz</code> backup file. Used for restore on a new server.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json.gz,.gz"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            className="block text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:py-1 file:text-sm file:cursor-pointer"
          />
          {uploadFile && (
            <p className="text-xs text-muted-foreground">Selected: <span className="font-mono">{uploadFile.name}</span> ({formatBytes(uploadFile.size)})</p>
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
              {t("settings_import_and_restore")}
            </button>
            <button onClick={() => { setRestoreTarget(null); setUploadFile(null); }} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
              {t("settings_cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Config */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{t("settings_auto_backup")}</p>
          {!editConfig && (
            <button onClick={openEdit} className="text-xs text-primary hover:underline">{t("settings_edit")}</button>
          )}
        </div>
        {configLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : editConfig ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">{t("settings_backup_enabled")}</span>
              <button
                onClick={() => setCfgEnabled((v) => !v)}
                className={cn("relative inline-flex h-6 w-11 items-center rounded-full transition-colors", cfgEnabled ? "bg-green-500" : "bg-muted-foreground/30")}
              >
                <span className={cn("inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform", cfgEnabled ? "translate-x-6" : "translate-x-1")} />
              </button>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">{t("settings_backup_interval")}</span>
              <input type="number" min={1} max={8760} value={cfgHours} onChange={(e) => setCfgHours(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-32 shrink-0">{t("settings_backup_keep")}</span>
              <input type="number" min={1} max={365} value={cfgKeep} onChange={(e) => setCfgKeep(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={() => configMutation.mutate({ enabled: cfgEnabled, interval_hours: cfgHours, keep_count: cfgKeep })}
                disabled={configMutation.isPending}
                className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-50">{t("settings_save")}</button>
              <button onClick={() => setEditConfig(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">{t("settings_cancel")}</button>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {([
              [t("settings_backup_status"), config?.enabled ? t("settings_enabled") : t("settings_disabled")],
              [t("settings_backup_interval"), t("settings_backup_interval_label", { n: config?.interval_hours ?? 24 })],
              [t("settings_backup_keep"), t("settings_backup_keep_label", { n: config?.keep_count ?? 7 })],
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
            {t("settings_smtp_note")}
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {t("settings_smtp_note_desc")}
          </p>
        </div>
      </div>

      {/* Backup list */}
      <div className="px-6 py-4">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">{t("settings_saved_backups")}</p>
        {listLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : !backups || backups.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("settings_backup_none")}</p>
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
                  title={t("settings_restore")}
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
                  title="Delete backup"
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

function ShopsSection({ readonly }: { readonly?: boolean }) {
  const { t } = useI18n();
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
        <h2 className="text-base font-semibold mb-4">{t("settings_shops_title")}</h2>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const shopList: Shop[] = shops ?? [];

  return (
    <div className={cn("rounded-lg border border-border bg-card", readonly && "opacity-60 pointer-events-none select-none")}>
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">{t("settings_shops_title")}</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t("settings_shops_desc")}
            </p>
          </div>
          {readonly && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Lock className="h-3.5 w-3.5" />
              {t("settings_read_only")}
            </div>
          )}
        </div>
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
            readonly={readonly}
          />
        ))}
        {shopList.length === 0 && (
          <p className="px-5 py-6 text-sm text-muted-foreground">
            {t("settings_no_shops")}
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
  readonly,
}: {
  shop: Shop;
  onToggle: (is_active: boolean) => void;
  isPending: boolean;
  readonly?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="flex-1 min-w-0">
        <p className="font-medium">{shop.name}</p>
        <p className="text-xs text-muted-foreground">
          {shop.domain} · {shop.default_provider} ·{" "}
          {shop.watch_count} watch{shop.watch_count !== 1 ? "es" : ""}
        </p>
      </div>

      {readonly ? (
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full font-medium",
          shop.is_active
            ? "bg-green-500/15 text-green-400"
            : "bg-slate-500/15 text-slate-400"
        )}>
          {shop.is_active ? t("settings_shop_active") : t("settings_shop_inactive")}
        </span>
      ) : (
        <button
          onClick={() => onToggle(!shop.is_active)}
          disabled={isPending}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 ${
            shop.is_active ? "bg-primary" : "bg-muted"
          }`}
          aria-label={shop.is_active ? t("settings_deactivate_shop") : t("settings_activate_shop")}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
              shop.is_active ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      )}
    </div>
  );
}

