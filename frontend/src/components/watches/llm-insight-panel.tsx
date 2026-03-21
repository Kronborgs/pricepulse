"use client";

import { Brain, Loader2, RefreshCw } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { LlmParserAdvice } from "@/types";
import { cn } from "@/lib/utils";

interface Props {
  sourceId: string;
  /** Existing cached analysis result (from last_diagnostic or DB) */
  existing?: LlmParserAdvice | null;
}

const CONFIDENCE_CLASS = (c: number) => {
  if (c >= 0.8) return "text-green-600 dark:text-green-400";
  if (c >= 0.5) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
};

const PAGE_TYPE_LABELS: Record<LlmParserAdvice["page_type"], string> = {
  product: "Produktside",
  listing: "Listelayout",
  blocked: "Blokeret",
  captcha: "CAPTCHA",
  unknown: "Ukendt",
};

export function LlmInsightPanel({ sourceId, existing }: Props) {
  const qc = useQueryClient();

  // Kick off a background diagnose job and poll the source for updated advice
  const diagnoseMutation = useMutation({
    mutationFn: () => api.sources.diagnose(sourceId),
    onSuccess: () => {
      // Give the background task a moment, then re-fetch source
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["source", sourceId] });
      }, 3000);
    },
  });

  const advice = existing;

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-500" />
          <h2 className="text-base font-semibold">AI-analyse</h2>
        </div>
        <button
          onClick={() => diagnoseMutation.mutate()}
          disabled={diagnoseMutation.isPending}
          className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors disabled:opacity-50"
        >
          {diagnoseMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Kør analyse
        </button>
      </div>

      <div className="p-5">
        {diagnoseMutation.isPending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4 rounded-md bg-muted/40 px-4 py-3">
            <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
            Starter Ollama-analyse i baggrunden…
          </div>
        )}

        {diagnoseMutation.isSuccess && !advice && (
          <div className="text-sm text-muted-foreground mb-4 rounded-md bg-muted/40 px-4 py-3">
            Analysen kører. Siden opdateres automatisk om et øjeblik.
          </div>
        )}

        {!advice ? (
          <p className="text-sm text-muted-foreground">
            Ingen AI-analyse tilgængelig endnu. Klik "Kør analyse" for at starte.
          </p>
        ) : (
          <div className="space-y-4">
            {/* Page type + confidence */}
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Sidetype</p>
                <p className="font-medium">{PAGE_TYPE_LABELS[advice.page_type]}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Konfidens</p>
                <p className={cn("font-semibold tabular-nums", CONFIDENCE_CLASS(advice.confidence))}>
                  {Math.round(advice.confidence * 100)}%
                </p>
              </div>
              {advice.requires_js && (
                <div className="rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400 px-2.5 py-0.5 text-xs font-medium">
                  Kræver JS
                </div>
              )}
              {advice.likely_bot_protection && (
                <div className="rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400 px-2.5 py-0.5 text-xs font-medium">
                  Bot-beskyttelse
                </div>
              )}
            </div>

            {/* Selectors */}
            {(advice.price_selector || advice.stock_selector) && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Foreslåede selectors</p>
                {advice.price_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-16 shrink-0">Pris</span>
                    <code className="flex-1 rounded bg-muted px-2 py-1 text-xs font-mono break-all">
                      {advice.price_selector}
                    </code>
                  </div>
                )}
                {advice.stock_selector && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-16 shrink-0">Lager</span>
                    <code className="flex-1 rounded bg-muted px-2 py-1 text-xs font-mono break-all">
                      {advice.stock_selector}
                    </code>
                  </div>
                )}
              </div>
            )}

            {/* Reasoning */}
            {advice.reasoning && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Begrundelse</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{advice.reasoning}</p>
              </div>
            )}

            {/* Recommended action */}
            {advice.recommended_action && (
              <div className="rounded-md bg-blue-50 dark:bg-blue-950/20 border border-blue-200/50 dark:border-blue-800/30 px-4 py-3">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  <span className="font-medium">Anbefaling: </span>
                  {advice.recommended_action}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
