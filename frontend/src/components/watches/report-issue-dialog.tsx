"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";

interface WatchOption {
  id: string;
  title: string | null;
  url: string;
}

interface ReportIssueDialogProps {
  /** Provide watchId for a single watch, or watches[] for multi-select (product page) */
  watchId?: string;
  watchTitle?: string | null;
  watches?: WatchOption[];
  onClose: () => void;
}

export function ReportIssueDialog({ watchId, watchTitle, watches, onClose }: ReportIssueDialogProps) {
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [selectedWatchId, setSelectedWatchId] = useState<string>(
    watchId ?? (watches?.[0]?.id ?? "")
  );
  const qc = useQueryClient();

  const effectiveWatchId = watchId ?? selectedWatchId;

  const mutation = useMutation({
    mutationFn: () => api.reports.create(effectiveWatchId, comment.trim() || undefined),
    onSuccess: () => {
      setSubmitted(true);
      qc.invalidateQueries({ queryKey: ["reports-unread"] });
    },
  });

  const getDomain = (url: string) => {
    try { return new URL(url).hostname.replace("www.", ""); } catch { return url; }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-400" />
            <h2 className="font-semibold text-base">Rapportér Data Webscraper problem</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {submitted ? (
          <div className="px-5 py-8 flex flex-col items-center gap-3 text-center">
            <CheckCircle2 className="h-10 w-10 text-green-500" />
            <p className="font-medium">Tak for din rapport!</p>
            <p className="text-sm text-muted-foreground">
              En administrator vil gennemgå rapporten og evt. forbedre scraperen.
            </p>
            <button
              onClick={onClose}
              className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Luk
            </button>
          </div>
        ) : (
          <div className="px-5 py-4 space-y-4">
            {/* Single watch title or multi-watch picker */}
            {watches && watches.length > 1 ? (
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="watch-select">
                  Hvilken butik/scraper handler det om?
                </label>
                <select
                  id="watch-select"
                  value={selectedWatchId}
                  onChange={(e) => setSelectedWatchId(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {watches.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.title ?? getDomain(w.url)}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              (watchTitle || watches?.[0]) && (
                <p className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">
                    {watchTitle ?? watches?.[0]?.title ?? getDomain(watches?.[0]?.url ?? "")}
                  </span>
                </p>
              )
            )}

            <p className="text-sm text-muted-foreground">
              Mener du at scraperen ikke viser de korrekte data? Beskriv kort hvad du oplever,
              så kan vi analysere og evt. bygge en bedre parser.
            </p>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="report-comment">
                Hvad er galt? <span className="text-muted-foreground">(valgfri)</span>
              </label>
              <textarea
                id="report-comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="F.eks. 'Prisen vises som 0', 'Titel er forkert', 'Ingen data hentes'…"
                rows={4}
                maxLength={1000}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <p className="text-xs text-muted-foreground text-right">{comment.length}/1000</p>
            </div>

            {mutation.isError && (
              <p className="text-sm text-destructive">
                Noget gik galt. Prøv igen om lidt.
              </p>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md px-4 py-2 text-sm hover:bg-muted transition-colors"
              >
                Annuller
              </button>
              <button
                type="button"
                disabled={mutation.isPending || !effectiveWatchId}
                onClick={() => mutation.mutate()}
                className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Send rapport
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
