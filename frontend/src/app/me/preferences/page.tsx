"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import {
  Loader2,
  CheckCircle,
  Send,
  Mail,
  Plus,
  Pencil,
  Trash2,
  Zap,
  BarChart2,
  Tag,
  Package,
  Globe,
  ChevronDown,
  ChevronUp,
  Play,
  Clock,
} from "lucide-react";
import { NotificationRule, NotificationRuleWrite } from "@/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useI18n } from "@/lib/i18n";

// ── Digest-info (sidst sendt + næste forventet) ────────────────────────────────────

const FREQ_MS: Record<string, number> = {
  hourly: 3600 * 1000,
  daily: 86400 * 1000,
  weekly: 7 * 86400 * 1000,
  monthly: 28 * 86400 * 1000,
};

function DigestInfo({ rule }: { rule: NotificationRule }) {
  const { t, locale } = useI18n();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  function formatLocalDT(dt: Date): string {
    const loc = locale === "da" ? "da-DK" : "en-GB";
    return dt.toLocaleString(loc, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const lastSent = rule.last_digest_sent_at ? new Date(rule.last_digest_sent_at) : null;
  const freq = rule.digest_frequency;
  const nextAt =
    lastSent && freq && FREQ_MS[freq]
      ? new Date(lastSent.getTime() + FREQ_MS[freq])
      : null;

  return (
    <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0">
      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
        <Clock className="h-3 w-3 shrink-0" />
        {t("prefs_last_sent")}: {lastSent ? formatLocalDT(lastSent) : t("prefs_never")}
      </span>
      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
        {t("prefs_next")}:{" "}
        {nextAt
          ? nextAt.getTime() > now
            ? formatLocalDT(nextAt)
            : t("prefs_ready")
          : t("prefs_first_run")}
      </span>
    </div>
  );
}

// ── Hjælpefunktioner ─────────────────────────────────────────────────────────

const FREQ_KEYS: Record<string, string> = {
  hourly: "prefs_freq_hourly",
  daily: "prefs_freq_daily",
  weekly: "prefs_freq_weekly",
  monthly: "prefs_freq_monthly",
};

const DAY_KEYS = [
  "prefs_day_mon", "prefs_day_tue", "prefs_day_wed", "prefs_day_thu",
  "prefs_day_fri", "prefs_day_sat", "prefs_day_sun",
];

const DAY_FULL_KEYS = [
  "prefs_day_monday", "prefs_day_tuesday", "prefs_day_wednesday", "prefs_day_thursday",
  "prefs_day_friday", "prefs_day_saturday", "prefs_day_sunday",
];

type TFn = (key: string, vars?: Record<string, unknown>) => string;

function filterSummary(rule: NotificationRule, t: TFn): string {
  if (rule.filter_mode === "tags" && rule.filter_tags?.length) {
    return `${t("prefs_filter_tags")}: ${rule.filter_tags.join(", ")}`;
  }
  if (rule.filter_mode === "products" && rule.filter_product_ids?.length) {
    return t("prefs_n_products", { n: rule.filter_product_ids.length });
  }
  return t("prefs_filter_all");
}

function eventSummary(rule: NotificationRule, t: TFn): string {
  const parts: string[] = [];
  if (rule.notify_price_drop) parts.push(t("prefs_event_price_drop"));
  if (rule.notify_back_in_stock) parts.push(t("prefs_event_stock"));
  if (rule.notify_on_change) parts.push(t("prefs_event_any_change"));
  if (rule.notify_new_error) parts.push(t("prefs_event_error"));
  return parts.join(", ") || t("prefs_event_none");
}

// ── Standard tom regel ────────────────────────────────────────────────────────
const EMPTY_RULE: NotificationRuleWrite = {
  name: "",
  enabled: true,
  rule_type: "instant",
  notify_price_drop: true,
  notify_back_in_stock: true,
  notify_on_change: false,
  notify_new_error: false,
  filter_mode: "all",
  filter_tags: null,
  filter_product_ids: null,
  digest_frequency: "daily",
  digest_day_of_week: 0,
};

// ── Regelformular (inline expand) ─────────────────────────────────────────────
interface RuleFormProps {
  initial: NotificationRuleWrite;
  allTags: string[];
  products: { id: string; name: string }[];
  onSave: (data: NotificationRuleWrite) => void;
  onCancel: () => void;
  saving: boolean;
}

function RuleForm({ initial, allTags, products, onSave, onCancel, saving }: RuleFormProps) {
  const { t } = useI18n();
  const [form, setForm] = useState<NotificationRuleWrite>({ ...initial });

  function setField<K extends keyof NotificationRuleWrite>(k: K, v: NotificationRuleWrite[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function toggleTag(tag: string) {
    const cur = form.filter_tags ?? [];
    const next = cur.includes(tag) ? cur.filter((t) => t !== tag) : [...cur, tag];
    setField("filter_tags", next.length ? next : null);
  }

  function toggleProduct(id: string) {
    const cur = form.filter_product_ids ?? [];
    const next = cur.includes(id) ? cur.filter((p) => p !== id) : [...cur, id];
    setField("filter_product_ids", next.length ? next : null);
  }

  return (
    <div className="rounded-lg border border-[#29ABE2]/40 bg-slate-800/60 p-4 space-y-4">
      {/* Navn */}
      <div>
        <label className="text-xs text-slate-400 block mb-1">{t("prefs_name_label")}</label>
        <input
          type="text"
          value={form.name ?? ""}
          onChange={(e) => setField("name", e.target.value || null)}
          placeholder="F.eks. Gaming — daglig digest"
          className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
        />
      </div>

      {/* Type */}
      <div>
        <label className="text-xs text-slate-400 block mb-2">{t("prefs_type_label")}</label>
        <div className="flex gap-3">
          {(["instant", "digest"] as const).map((rtype) => (
            <button
              key={rtype}
              type="button"
              onClick={() => setField("rule_type", rtype)}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium border transition-colors ${
                form.rule_type === rtype
                  ? "bg-[#29ABE2] border-[#29ABE2] text-white"
                  : "border-slate-600 text-slate-400 hover:border-slate-400"
              }`}
            >
              {rtype === "instant" ? <Zap className="h-3.5 w-3.5" /> : <BarChart2 className="h-3.5 w-3.5" />}
              {rtype === "instant" ? t("prefs_instant") : "Digest"}
            </button>
          ))}
        </div>
      </div>

      {/* Hændelsestyper */}
      <div>
        <label className="text-xs text-slate-400 block mb-2">{t("prefs_triggers_label")}</label>
        <div className="grid grid-cols-2 gap-2">
          {(
            [
              { field: "notify_price_drop" as const, label: t("prefs_price_drop") },
              { field: "notify_back_in_stock" as const, label: t("prefs_back_in_stock") },
              { field: "notify_on_change" as const, label: t("prefs_any_change") },
              { field: "notify_new_error" as const, label: t("prefs_scan_error") },
            ] as const
          ).map(({ field, label }) => (
            <label key={field} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!form[field]}
                onChange={() => setField(field, !form[field])}
                className="rounded"
              />
              <span className="text-sm text-slate-200">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Digest-frekvens */}
      {form.rule_type === "digest" && (
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">{t("prefs_frequency")}</label>
            <select
              value={form.digest_frequency ?? "daily"}
              onChange={(e) => setField("digest_frequency", e.target.value as NotificationRuleWrite["digest_frequency"])}
              className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
            >
              <option value="hourly">{t("prefs_freq_hourly")}</option>
              <option value="daily">{t("prefs_freq_daily")}</option>
              <option value="weekly">{t("prefs_freq_weekly")}</option>
              <option value="monthly">{t("prefs_freq_monthly")}</option>
            </select>
          </div>
          {form.digest_frequency === "weekly" && (
            <div>
              <label className="text-xs text-slate-400 block mb-1">{t("prefs_day")}</label>
              <select
                value={form.digest_day_of_week ?? 0}
                onChange={(e) => setField("digest_day_of_week", Number(e.target.value))}
                className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              >
                {["prefs_day_monday", "prefs_day_tuesday", "prefs_day_wednesday", "prefs_day_thursday", "prefs_day_friday", "prefs_day_saturday", "prefs_day_sunday"].map((key, i) => (
                  <option key={i} value={i}>{t(key)}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Produktfilter */}
      <div>
        <label className="text-xs text-slate-400 block mb-2">{t("prefs_product_filter")}</label>
        <div className="flex gap-3 flex-wrap">
          {(
            [
              { value: "all", icon: <Globe className="h-3.5 w-3.5" />, label: t("prefs_filter_all") },
              { value: "tags", icon: <Tag className="h-3.5 w-3.5" />, label: t("prefs_filter_tags") },
              { value: "products", icon: <Package className="h-3.5 w-3.5" />, label: t("products_title") },
            ] as const
          ).map(({ value, icon, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setField("filter_mode", value);
                if (value !== "tags") setField("filter_tags", null);
                if (value !== "products") setField("filter_product_ids", null);
              }}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium border transition-colors ${
                form.filter_mode === value
                  ? "bg-[#29ABE2] border-[#29ABE2] text-white"
                  : "border-slate-600 text-slate-400 hover:border-slate-400"
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* Tag-vælger */}
        {form.filter_mode === "tags" && (
          <div className="mt-3 flex flex-wrap gap-2">
            {allTags.length === 0 ? (
              <p className="text-xs text-slate-500">{t("prefs_no_tags")}</p>
            ) : (
              allTags.map((tag) => {
                const active = (form.filter_tags ?? []).includes(tag);
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => toggleTag(tag)}
                    className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                      active
                        ? "bg-[#29ABE2] border-[#29ABE2] text-white"
                        : "border-slate-600 text-slate-400 hover:border-slate-400"
                    }`}
                  >
                    {tag}
                  </button>
                );
              })
            )}
          </div>
        )}

        {/* Produkt-vælger */}
        {form.filter_mode === "products" && (
          <div className="mt-3 max-h-40 overflow-y-auto space-y-1 border border-slate-700 rounded-md p-2">
            {products.length === 0 ? (
              <p className="text-xs text-slate-500 p-1">{t("products_none_found")}</p>
            ) : (
              products.map((p) => {
                const active = (form.filter_product_ids ?? []).includes(p.id);
                return (
                  <label key={p.id} className="flex items-center gap-2 cursor-pointer py-0.5">
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleProduct(p.id)}
                      className="rounded"
                    />
                    <span className="text-sm text-slate-200 truncate">{p.name}</span>
                  </label>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Knapper */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          disabled={saving}
          onClick={() => onSave(form)}
          className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {t("prefs_save_rule")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700"
        >
          {t("settings_cancel")}
        </button>
      </div>
    </div>
  );
}

// ── Regelkort ────────────────────────────────────────────────────────────────
interface RuleCardProps {
  rule: NotificationRule;
  allTags: string[];
  products: { id: string; name: string }[];
  onToggle: () => void;
  onSave: (data: NotificationRuleWrite) => void;
  onDelete: () => void;
  deleting: boolean;
  saving: boolean;
}

function RuleCard({ rule, allTags, products, onToggle, onSave, onDelete, deleting, saving }: RuleCardProps) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [optimisticEnabled, setOptimisticEnabled] = useState<boolean | null>(null);
  const [runSent, setRunSent] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const runMutation = useMutation({
    mutationFn: () => api.notificationRules.run(rule.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me", "notification-rules"] });
      setRunSent(true);
      setRunError(null);
      setTimeout(() => setRunSent(false), 5000);
    },
    onError: (err: Error) => {
      setRunError(err.message ?? t("prefs_smtp_error"));
      setTimeout(() => setRunError(null), 6000);
    },
  });

  // Reset optimistic state when server responds with confirmed value
  useEffect(() => {
    if (optimisticEnabled !== null && optimisticEnabled === rule.enabled) {
      setOptimisticEnabled(null);
    }
  }, [rule.enabled, optimisticEnabled]);

  const enabled = optimisticEnabled ?? rule.enabled;

  function handleToggle() {
    setOptimisticEnabled(!rule.enabled);
    onToggle();
  }

  return (
    <div
      className={`rounded-lg border bg-slate-900 ${
        enabled ? "border-slate-700" : "border-slate-800 opacity-60"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Typebadge */}
        <span
          className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            rule.rule_type === "instant"
              ? "bg-amber-900/40 text-amber-300"
              : "bg-blue-900/40 text-blue-300"
          }`}
        >
          {rule.rule_type === "instant" ? (
            <Zap className="h-3 w-3" />
          ) : (
            <BarChart2 className="h-3 w-3" />
          )}
          {rule.rule_type === "instant" ? t("prefs_instant") : "Digest"}
        </span>

        {/* Navn / sammendrag */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">
            {rule.name || (rule.rule_type === "digest"
              ? `${t(FREQ_KEYS[rule.digest_frequency ?? "daily"] ?? "prefs_freq_daily")}`
              : t("prefs_instant_notification"))}
          </p>
          <p className="text-xs text-slate-500 truncate">
            {filterSummary(rule, t)}
            {rule.rule_type === "digest" && rule.digest_frequency && (
              <> · {t(FREQ_KEYS[rule.digest_frequency] ?? "prefs_freq_daily")}
                {rule.digest_frequency === "weekly" && rule.digest_day_of_week != null
                  ? ` (${t(DAY_KEYS[rule.digest_day_of_week] ?? "prefs_day_mon")})`
                  : ""}
              </>
            )}
            {rule.rule_type === "instant" && (
              <> · {eventSummary(rule, t)}</>
            )}
          </p>
          {rule.rule_type === "digest" && (
            <div className="mt-0.5">
              <DigestInfo rule={rule} />
            </div>
          )}
        </div>

        {/* Handlinger */}
        <div className="flex items-center gap-1">
          {/* Kør nu-knap */}
          <button
            type="button"
            title={t("prefs_run_now")}
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="rounded p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 disabled:opacity-40"
          >
            {runMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : runSent ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </button>
          {/* Toggle enabled */}
          <button
            type="button"
            onClick={handleToggle}
            aria-label={enabled ? t("prefs_deactivate") : t("prefs_activate")}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50 ${
              enabled ? "bg-[#29ABE2]" : "bg-slate-600"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="rounded p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700"
          >
            {editing ? <ChevronUp className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={deleting}
            className="rounded p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-700 disabled:opacity-40"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Test feedback */}
      {(runSent || runError) && (
        <div className={`mx-4 mb-3 rounded-md px-3 py-2 text-xs flex items-center gap-2 ${runSent ? "bg-emerald-900/40 text-emerald-300" : "bg-red-900/40 text-red-300"}`}>
          {runSent && <CheckCircle className="h-3.5 w-3.5 shrink-0" />}
          {runSent ? t("prefs_email_sent") : runError}
        </div>
      )}

      {/* Redigeringsformular */}
      {editing && (
        <div className="border-t border-slate-700 p-4">
          <RuleForm
            initial={{
              name: rule.name,
              enabled: rule.enabled,
              rule_type: rule.rule_type,
              notify_price_drop: rule.notify_price_drop,
              notify_back_in_stock: rule.notify_back_in_stock,
              notify_on_change: rule.notify_on_change,
              notify_new_error: rule.notify_new_error,
              filter_mode: rule.filter_mode,
              filter_tags: rule.filter_tags,
              filter_product_ids: rule.filter_product_ids,
              digest_frequency: rule.digest_frequency,
              digest_day_of_week: rule.digest_day_of_week,
            }}
            allTags={allTags}
            products={products}
            saving={saving}
            onSave={(data) => {
              onSave(data);
              setEditing(false);
            }}
            onCancel={() => setEditing(false)}
          />
        </div>
      )}
    </div>
  );
}

// ── Hovedside ──────────────────────────────────────────────────────────────────
export default function PreferencesPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { data: me } = useCurrentUser();

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ["me", "notification-rules"],
    queryFn: () => api.notificationRules.list(),
  });

  const { data: productsData } = useQuery({
    queryKey: ["products", "my", me?.id],
    queryFn: () => api.products.list({ owner_ids: [me!.id], limit: 200 }),
    enabled: !!me?.id,
  });

  const [adding, setAdding] = useState(false);
  const [testSent, setTestSent] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const allTags = Array.from(
    new Set((productsData?.items ?? []).flatMap((p) => p.tags ?? []))
  ).sort();

  const productOptions = (productsData?.items ?? []).map((p) => ({
    id: p.id,
    name: p.name,
  }));

  const createMutation = useMutation({
    mutationFn: (data: NotificationRuleWrite) => api.notificationRules.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me", "notification-rules"] });
      setAdding(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NotificationRuleWrite> }) =>
      api.notificationRules.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me", "notification-rules"] });
      setSavingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.notificationRules.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me", "notification-rules"] });
      setDeletingId(null);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => api.emailPreferences.sendTest(),
    onSuccess: () => {
      setTestSent(true);
      setTimeout(() => setTestSent(false), 4000);
    },
  });

  return (
    <AuthGuard>
      <div className="space-y-6 max-w-xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("prefs_title")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("prefs_subtitle")}
          </p>
        </div>

        {/* Regler */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">{t("prefs_rules")}</h2>
            {!adding && (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="flex items-center gap-1.5 rounded-md bg-[#29ABE2] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#29ABE2]/90"
              >
                <Plus className="h-3.5 w-3.5" /> {t("prefs_add_rule")}
              </button>
            )}
          </div>

          {rulesLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
            </div>
          ) : rules.length === 0 && !adding ? (
            <div className="rounded-lg border border-dashed border-slate-700 p-8 text-center">
              <p className="text-sm text-slate-500 mb-3">
                {t("prefs_no_rules")}
              </p>
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="flex items-center gap-1.5 mx-auto rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90"
              >
                <Plus className="h-4 w-4" /> {t("prefs_create_first")}
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <RuleCard
                  key={rule.id}
                  rule={rule}
                  allTags={allTags}
                  products={productOptions}
                  saving={savingId === rule.id && updateMutation.isPending}
                  deleting={deletingId === rule.id && deleteMutation.isPending}
                  onToggle={() => {
                    setSavingId(rule.id);
                    updateMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } });
                  }}
                  onSave={(data) => {
                    setSavingId(rule.id);
                    updateMutation.mutate({ id: rule.id, data });
                  }}
                  onDelete={() => {
                    setDeletingId(rule.id);
                    deleteMutation.mutate(rule.id);
                  }}
                />
              ))}
            </div>
          )}

          {/* Ny-regel-formular */}
          {adding && (
            <RuleForm
              initial={EMPTY_RULE}
              allTags={allTags}
              products={productOptions}
              saving={createMutation.isPending}
              onSave={(data) => createMutation.mutate(data)}
              onCancel={() => setAdding(false)}
            />
          )}
        </div>

        {/* Hjælpetekst + test-knap */}
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-300">{t("prefs_types_explained")}</h2>
          <div className="space-y-2 text-xs text-slate-500">
            <p>
              <span className="text-amber-300 font-medium">{t("prefs_instant")}</span> — {t("prefs_instant_desc").replace(t("prefs_instant") + " — ", "")}
            </p>
            <p>
              <span className="text-blue-300 font-medium">Digest</span> — {t("prefs_digest_desc").replace("Digest — ", "")}
            </p>
            <p>{t("prefs_multi_rules")}</p>
          </div>

          <button
            type="button"
            disabled={testMutation.isPending}
            onClick={() => testMutation.mutate()}
            className="flex items-center gap-2 rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-60"
          >
            {testMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {t("prefs_send_test")}
          </button>

          {testMutation.isError && (
            <span className="text-xs text-red-400">
              {(testMutation.error as Error)?.message || t("prefs_smtp_error")}
            </span>
          )}
          {testSent && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <Mail className="h-3 w-3" /> {t("prefs_test_sent")}
            </span>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
