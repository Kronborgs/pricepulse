"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Search, CheckCircle, AlertCircle, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";
import { formatPrice, getDomain } from "@/lib/utils";
import { WatchDetectResult } from "@/types";

const schema = z.object({
  url: z.string().url("Angiv en gyldig URL (inkl. https://)"),
  check_interval: z.coerce.number().min(5).max(10080).default(60),
});

type FormData = z.infer<typeof schema>;

export function AddWatchDialog() {
  const [open, setOpen] = useState(false);
  const [detected, setDetected] = useState<WatchDetectResult | null>(null);
  const [detecting, setDetecting] = useState(false);

  const qc = useQueryClient();
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { check_interval: 60 },
  });

  const urlValue = watch("url");

  const createMutation = useMutation({
    mutationFn: api.watches.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watches"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      setOpen(false);
      reset();
      setDetected(null);
    },
  });

  async function handleDetect() {
    if (!urlValue) return;
    setDetecting(true);
    try {
      const result = await api.watches.detect(urlValue);
      setDetected(result);
    } catch {
      setDetected({ url: urlValue, error: "Kunne ikke hente siden", detected_title: null, detected_price: null, detected_currency: null, detected_stock: null, detected_image_url: null, suggested_provider: "http", suggested_price_selector: null, confidence: "low", shop_domain: null });
    } finally {
      setDetecting(false);
    }
  }

  async function onSubmit(data: FormData) {
    createMutation.mutate({
      url: data.url,
      check_interval: data.check_interval,
      provider: detected?.suggested_provider ?? "http",
    });
  }

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
      <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold">Tilføj ny watch</h2>
          <button onClick={() => { setOpen(false); reset(); setDetected(null); }} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
          {/* URL input */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Produkt URL</label>
            <div className="flex gap-2">
              <input
                {...register("url")}
                placeholder="https://www.komplett.dk/product/..."
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                type="button"
                onClick={handleDetect}
                disabled={detecting || !urlValue}
                className="inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-2 text-sm hover:bg-accent disabled:opacity-50 transition-colors"
              >
                {detecting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {detecting ? "Henter…" : "Detect"}
              </button>
            </div>
            {errors.url && (
              <p className="text-xs text-destructive">{errors.url.message}</p>
            )}
          </div>

          {/* Detection result */}
          {detected && (
            <div className={`rounded-lg p-3 text-sm space-y-2 ${detected.error ? "bg-destructive/10 border border-destructive/20" : "bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30"}`}>
              {detected.error ? (
                <div className="flex items-start gap-2 text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <span>{detected.error}</span>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-green-600" />
                  <div className="space-y-1">
                    {detected.detected_title && (
                      <p className="font-medium line-clamp-1">{detected.detected_title}</p>
                    )}
                    <div className="flex items-center gap-3 text-muted-foreground">
                      {detected.detected_price && (
                        <span className="font-mono font-semibold text-foreground">
                          {formatPrice(detected.detected_price, detected.detected_currency ?? "DKK")}
                        </span>
                      )}
                      {detected.detected_stock && (
                        <span>{detected.detected_stock === "in_stock" ? "✓ På lager" : "✗ Udsolgt"}</span>
                      )}
                      <span className="text-xs">
                        Confidence: <strong>{detected.confidence}</strong>
                      </span>
                    </div>
                    {detected.suggested_provider === "playwright" && (
                      <p className="text-xs text-orange-600 dark:text-orange-400">
                        ⚠ Siden kræver browser-rendering (Playwright)
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Check interval */}
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

          {/* Shop domain readout */}
          {detected?.shop_domain && (
            <p className="text-xs text-muted-foreground">
              Shop: <strong>{detected.shop_domain}</strong> · Provider: <strong>{detected.suggested_provider}</strong>
            </p>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => { setOpen(false); reset(); setDetected(null); }}
              className="rounded-md px-4 py-2 text-sm border border-border hover:bg-accent transition-colors"
            >
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
      </div>
    </div>
  );
}
