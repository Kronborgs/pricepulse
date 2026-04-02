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
  FlaskConical,
  Clock,
} from "lucide-react";
import { NotificationRule, NotificationRuleWrite } from "@/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";

// ── Digest-nedtæller ─────────────────────────────────────────────────────────

const FREQ_MS: Record<string, number> = {
  hourly: 3600 * 1000,
  daily: 86400 * 1000,
  weekly: 7 * 86400 * 1000,
  monthly: 28 * 86400 * 1000,
};

function nextDigestAt(rule: NotificationRule): Date | null {
  if (rule.rule_type !== "digest" || !rule.digest_frequency) return null;
  const base = rule.last_digest_sent_at
    ? new Date(rule.last_digest_sent_at)
    : new Date(Date.now() - (FREQ_MS[rule.digest_frequency] ?? 0)); // treat as just sent = due now
  return new Date(base.getTime() + (FREQ_MS[rule.digest_frequency] ?? 0));
}

function formatCountdown(ms: number): string {
  if (ms <= 0) return "Snart";
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  if (h > 0) return `${h}t ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function DigestCountdown({ rule }: { rule: NotificationRule }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const target = nextDigestAt(rule);
  if (!target) return null;
  const remaining = target.getTime() - now;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-500">
      <Clock className="h-3 w-3" />
      {remaining <= 0 ? "Klar til afsendelse" : `Næste om ${formatCountdown(remaining)}`}
    </span>
  );
}

// ── Hjælpefunktioner ─────────────────────────────────────────────────────────

const FREQ_LABELS: Record<string, string> = {
  hourly: "Hver time",
  daily: "Daglig",
  weekly: "Ugentlig",
  monthly: "Månedlig",
};

const DAY_LABELS = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"];

function filterSummary(rule: NotificationRule): string {
  if (rule.filter_mode === "tags" && rule.filter_tags?.length) {
    return `Tags: ${rule.filter_tags.join(", ")}`;
  }
  if (rule.filter_mode === "products" && rule.filter_product_ids?.length) {
    return `${rule.filter_product_ids.length} produkt${rule.filter_product_ids.length !== 1 ? "er" : ""}`;
  }
  return "Alle produkter";
}

function eventSummary(rule: NotificationRule): string {
  const parts: string[] = [];
  if (rule.notify_price_drop) parts.push("Prisfald");
  if (rule.notify_back_in_stock) parts.push("Lager");
  if (rule.notify_on_change) parts.push("Enhver ændring");
  if (rule.notify_new_error) parts.push("Fejl");
  return parts.join(", ") || "Ingen";
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
        <label className="text-xs text-slate-400 block mb-1">Navn (valgfrit)</label>
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
        <label className="text-xs text-slate-400 block mb-2">Type</label>
        <div className="flex gap-3">
          {(["instant", "digest"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setField("rule_type", t)}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium border transition-colors ${
                form.rule_type === t
                  ? "bg-[#29ABE2] border-[#29ABE2] text-white"
                  : "border-slate-600 text-slate-400 hover:border-slate-400"
              }`}
            >
              {t === "instant" ? <Zap className="h-3.5 w-3.5" /> : <BarChart2 className="h-3.5 w-3.5" />}
              {t === "instant" ? "Øjeblikkelig" : "Digest"}
            </button>
          ))}
        </div>
      </div>

      {/* Hændelsestyper */}
      <div>
        <label className="text-xs text-slate-400 block mb-2">Hvad skal udløse notifikationen?</label>
        <div className="grid grid-cols-2 gap-2">
          {(
            [
              { field: "notify_price_drop" as const, label: "Prisfald" },
              { field: "notify_back_in_stock" as const, label: "Tilbage på lager" },
              { field: "notify_on_change" as const, label: "Enhver ændring" },
              { field: "notify_new_error" as const, label: "Fejl ved skanning" },
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
            <label className="text-xs text-slate-400 block mb-1">Frekvens</label>
            <select
              value={form.digest_frequency ?? "daily"}
              onChange={(e) => setField("digest_frequency", e.target.value as NotificationRuleWrite["digest_frequency"])}
              className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
            >
              <option value="hourly">Hver time</option>
              <option value="daily">Daglig</option>
              <option value="weekly">Ugentlig</option>
              <option value="monthly">Månedlig</option>
            </select>
          </div>
          {form.digest_frequency === "weekly" && (
            <div>
              <label className="text-xs text-slate-400 block mb-1">Dag</label>
              <select
                value={form.digest_day_of_week ?? 0}
                onChange={(e) => setField("digest_day_of_week", Number(e.target.value))}
                className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              >
                {["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"].map((d, i) => (
                  <option key={i} value={i}>{d}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Produktfilter */}
      <div>
        <label className="text-xs text-slate-400 block mb-2">Produktfilter</label>
        <div className="flex gap-3 flex-wrap">
          {(
            [
              { value: "all", icon: <Globe className="h-3.5 w-3.5" />, label: "Alle" },
              { value: "tags", icon: <Tag className="h-3.5 w-3.5" />, label: "Tags" },
              { value: "products", icon: <Package className="h-3.5 w-3.5" />, label: "Produkter" },
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
              <p className="text-xs text-slate-500">Ingen tags på dine produkter</p>
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
              <p className="text-xs text-slate-500 p-1">Ingen produkter fundet</p>
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
          Gem regel
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700"
        >
          Annuller
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
  const [editing, setEditing] = useState(false);
  const [optimisticEnabled, setOptimisticEnabled] = useState<boolean | null>(null);
  const [testSent, setTestSent] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  const testMutation = useMutation({
    mutationFn: () => api.notificationRules.test(rule.id),
    onSuccess: () => {
      setTestSent(true);
      setTestError(null);
      setTimeout(() => setTestSent(false), 4000);
    },
    onError: (err: Error) => {
      setTestError(err.message ?? "Fejl ved afsendelse");
      setTimeout(() => setTestError(null), 5000);
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
          {rule.rule_type === "instant" ? "Øjeblikkelig" : "Digest"}
        </span>

        {/* Navn / sammendrag */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">
            {rule.name || (rule.rule_type === "digest"
              ? `${FREQ_LABELS[rule.digest_frequency ?? "daily"] ?? "Digest"}`
              : "Øjeblikkelig notifikation")}
          </p>
          <p className="text-xs text-slate-500 truncate">
            {filterSummary(rule)}
            {rule.rule_type === "digest" && rule.digest_frequency && (
              <> · {FREQ_LABELS[rule.digest_frequency]}
                {rule.digest_frequency === "weekly" && rule.digest_day_of_week != null
                  ? ` (${DAY_LABELS[rule.digest_day_of_week]})`
                  : ""}
              </>
            )}
            {rule.rule_type === "instant" && (
              <> · {eventSummary(rule)}</>
            )}
          </p>
          {rule.rule_type === "digest" && (
            <div className="mt-0.5">
              <DigestCountdown rule={rule} />
            </div>
          )}
        </div>

        {/* Handlinger */}
        <div className="flex items-center gap-1">
          {/* Test-knap */}
          <button
            type="button"
            title="Send test-email"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="rounded p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 disabled:opacity-40"
          >
            {testMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : testSent ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <FlaskConical className="h-4 w-4" />
            )}
          </button>
          {/* Toggle enabled */}
          <button
            type="button"
            onClick={handleToggle}
            aria-label={enabled ? "Deaktivér" : "Aktivér"}
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
      {(testSent || testError) && (
        <div className={`mx-4 mb-3 rounded-md px-3 py-2 text-xs flex items-center gap-2 ${testSent ? "bg-emerald-900/40 text-emerald-300" : "bg-red-900/40 text-red-300"}`}>
          {testSent ? <CheckCircle className="h-3.5 w-3.5 shrink-0" /> : null}
          {testSent ? "Test-email afsendt — tjek din indbakke" : testError}
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
          <h1 className="text-2xl font-bold tracking-tight">Notifikationspræferencer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Opret notifikationsregler med individuelle produktfiltre og intervaller
          </p>
        </div>

        {/* Regler */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">Regler</h2>
            {!adding && (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="flex items-center gap-1.5 rounded-md bg-[#29ABE2] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#29ABE2]/90"
              >
                <Plus className="h-3.5 w-3.5" /> Tilføj regel
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
                Du har ingen notifikationsregler endnu.
              </p>
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="flex items-center gap-1.5 mx-auto rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90"
              >
                <Plus className="h-4 w-4" /> Opret første regel
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
          <h2 className="text-sm font-semibold text-slate-300">Typer forklaret</h2>
          <div className="space-y-2 text-xs text-slate-500">
            <p>
              <span className="text-amber-300 font-medium">Øjeblikkelig</span> — sendes straks
              når prisen falder eller lager ændres, baseret på om produktet matcher din regel.
            </p>
            <p>
              <span className="text-blue-300 font-medium">Digest</span> — en samlet oversigt
              over alle ændringer inden for perioden (time/dag/uge/måned). Sendes automatisk
              når intervallet udløber.
            </p>
            <p>
              Du kan have <span className="text-slate-300">flere regler</span> — f.eks. en
              digest for gaming-produkter dagligt og øjeblikkelige notifikationer for alle
              andre.
            </p>
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
            Send test-e-mail
          </button>

          {testMutation.isError && (
            <span className="text-xs text-red-400">
              {(testMutation.error as Error)?.message || "Fejl — er SMTP konfigureret?"}
            </span>
          )}
          {testSent && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <Mail className="h-3 w-3" /> Test-e-mail sendt
            </span>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
