"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, CheckCircle, Loader2, X, List, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { getDomain } from "@/lib/utils";

const schema = z.object({
  url: z.string().url("Angiv en gyldig URL (inkl. https://)"),
  check_interval: z.coerce.number().min(5).max(10080).default(360),
});

type FormData = z.infer<typeof schema>;

// ── Bulk-tilstand ─────────────────────────────────────────────────────────────

type BulkItemStatus = "pending" | "adding" | "ok" | "error";

interface BulkItem {
  url: string;
  status: BulkItemStatus;
  error?: string;
}

function parseBulkText(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter((s) => {
      try { new URL(s); return true; } catch { return false; }
    });
}

export function AddWatchDialog() {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [lastAdded, setLastAdded] = useState<string | null>(null);

  // Bulk state
  const [bulkText, setBulkText] = useState("");
  const [bulkInterval, setBulkInterval] = useState(360);
  const [bulkItems, setBulkItems] = useState<BulkItem[] | null>(null);
  const [bulkRunning, setBulkRunning] = useState(false);

  const qc = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { check_interval: 360 },
  });

  const createMutation = useMutation({
    mutationFn: api.watches.create,
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["watches"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      setLastAdded(getDomain(variables.url));
      reset();
      setTimeout(() => setLastAdded(null), 4000);
    },
  });

  async function onSubmit(data: FormData) {
    createMutation.mutate({
      url: data.url,
      check_interval: data.check_interval,
      provider: "http",
    });
  }

  function handleClose() {
    setOpen(false);
    reset();
    setBulkText("");
    setBulkItems(null);
    setBulkRunning(false);
  }

  // ── Bulk-logik ──────────────────────────────────────────────────────────────

  const bulkUrls = parseBulkText(bulkText);

  async function runBulk() {
    const urls = bulkUrls;
    if (!urls.length) return;
    const items: BulkItem[] = urls.map((url) => ({ url, status: "pending" }));
    setBulkItems([...items]);
    setBulkRunning(true);

    for (let i = 0; i < items.length; i++) {
      items[i].status = "adding";
      setBulkItems([...items]);
      try {
        await api.watches.create({ url: items[i].url, check_interval: bulkInterval, provider: "http" });
        items[i].status = "ok";
      } catch (err: unknown) {
        items[i].status = "error";
        items[i].error = err instanceof Error ? err.message : "Ukendt fejl";
      }
      setBulkItems([...items]);
    }

    setBulkRunning(false);
    qc.invalidateQueries({ queryKey: ["watches"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  }

  function bulkSummary() {
    if (!bulkItems) return null;
    const ok = bulkItems.filter((i) => i.status === "ok").length;
    const err = bulkItems.filter((i) => i.status === "error").length;
    const pending = bulkItems.filter((i) => i.status === "pending" || i.status === "adding").length;
    return { ok, err, pending };
  }

  const summary = bulkSummary();
  const bulkDone = bulkItems && !bulkRunning;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        <Plus className="h-4 w-4" />
        Tilføj watch
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-lg font-semibold">Tilføj watches</h2>
          <button onClick={handleClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Mode tabs */}
        <div className="flex border-b border-border shrink-0">
          <button
            onClick={() => setMode("single")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              mode === "single"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Enkelt URL
          </button>
          <button
            onClick={() => setMode("bulk")}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
              mode === "bulk"
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="h-3.5 w-3.5" />
            Bulk (liste)
          </button>
        </div>

        <div className="overflow-y-auto flex-1">
          {/* ── Enkelt-tilstand ── */}
          {mode === "single" && (
            <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
              {lastAdded && (
                <div className="flex items-center gap-2 rounded-lg bg-[#8DC63F]/10 border border-[#8DC63F]/25 px-3 py-2 text-sm text-[#8DC63F]">
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  <span><strong>{lastAdded}</strong> tilføjet — indtast ny URL for at fortsætte</span>
                </div>
              )}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Produkt URL</label>
                <input
                  {...register("url")}
                  placeholder="https://www.komplett.dk/product/..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                {errors.url && (
                  <p className="text-xs text-destructive">{errors.url.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Tjek-interval</label>
                <select
                  {...register("check_interval")}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value={15}>Hver 15 minutter</option>
                  <option value={30}>Hver 30 minutter</option>
                  <option value={60}>Hver time</option>
                  <option value={360}>Hver 6. time</option>
                  <option value={720}>To gange dagligt</option>
                  <option value={1440}>Dagligt</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={handleClose} className="rounded-md px-4 py-2 text-sm border border-border hover:bg-accent transition-colors">
                  Annuller
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Tilføj watch
                </button>
              </div>
            </form>
          )}

          {/* ── Bulk-tilstand ── */}
          {mode === "bulk" && (
            <div className="p-5 space-y-4">
              {!bulkItems ? (
                <>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">URLs — én per linje</label>
                    <textarea
                      value={bulkText}
                      onChange={(e) => setBulkText(e.target.value)}
                      rows={10}
                      placeholder={
                        "https://www.komplett.dk/product/...\nhttps://www.elgiganten.dk/product/...\nhttps://www.power.dk/..."
                      }
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y"
                    />
                    {bulkUrls.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {bulkUrls.length} gyldige URL{bulkUrls.length !== 1 ? "s" : ""} fundet
                      </p>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Tjek-interval (for alle)</label>
                    <select
                      value={bulkInterval}
                      onChange={(e) => setBulkInterval(Number(e.target.value))}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value={15}>Hver 15 minutter</option>
                      <option value={30}>Hver 30 minutter</option>
                      <option value={60}>Hver time</option>
                      <option value={360}>Hver 6. time</option>
                      <option value={720}>To gange dagligt</option>
                      <option value={1440}>Dagligt</option>
                    </select>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <button type="button" onClick={handleClose} className="rounded-md px-4 py-2 text-sm border border-border hover:bg-accent transition-colors">
                      Annuller
                    </button>
                    <button
                      onClick={runBulk}
                      disabled={bulkUrls.length === 0}
                      className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      Tilføj {bulkUrls.length > 0 ? `${bulkUrls.length} watches` : "watches"}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* Progress / resultatliste */}
                  {summary && (
                    <div className="flex items-center gap-3 text-sm">
                      {summary.ok > 0 && (
                        <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                          <CheckCircle className="h-4 w-4" />
                          {summary.ok} tilføjet
                        </span>
                      )}
                      {summary.err > 0 && (
                        <span className="flex items-center gap-1 text-destructive">
                          <AlertCircle className="h-4 w-4" />
                          {summary.err} fejl
                        </span>
                      )}
                      {bulkRunning && summary.pending > 0 && (
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {summary.pending} tilbage…
                        </span>
                      )}
                    </div>
                  )}

                  <div className="rounded-md border border-border divide-y divide-border max-h-72 overflow-y-auto">
                    {bulkItems.map((item, i) => (
                      <div key={i} className="flex items-start gap-3 px-3 py-2.5">
                        <div className="mt-0.5 shrink-0">
                          {item.status === "ok" && <CheckCircle className="h-4 w-4 text-green-500" />}
                          {item.status === "error" && <AlertCircle className="h-4 w-4 text-destructive" />}
                          {item.status === "adding" && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                          {item.status === "pending" && <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-mono truncate text-foreground">{item.url}</p>
                          {item.error && (
                            <p className="text-xs text-destructive mt-0.5">{item.error}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {bulkDone && (
                    <div className="flex justify-end gap-3 pt-2">
                      <button
                        onClick={() => { setBulkItems(null); setBulkText(""); }}
                        className="rounded-md px-4 py-2 text-sm border border-border hover:bg-accent transition-colors"
                      >
                        Tilføj flere
                      </button>
                      <button
                        onClick={handleClose}
                        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                      >
                        Færdig
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

