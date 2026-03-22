"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { Loader2, Trash2, RefreshCw } from "lucide-react";

interface StatRow {
  label: string;
  key: keyof Awaited<ReturnType<typeof api.adminData.stats>>;
  description: string;
  deleteKey: "deleteWatches" | "deleteProducts" | "deletePriceHistory" | "deleteAiJobs" | "deleteEmailQueue" | null;
  deleteLabel: string;
  confirmText: string;
}

const rows: StatRow[] = [
  {
    label: "Watches (v1)",
    key: "watches_v1",
    description: "Overvågninger oprettet med det gamle system",
    deleteKey: "deleteWatches",
    deleteLabel: "Slet alle watches",
    confirmText: "Slet ALLE watches (v1 + v2) inkl. prishistorik?\n\nHandlingen kan ikke fortrydes.",
  },
  {
    label: "Watches (v2)",
    key: "watches_v2",
    description: "Overvågninger oprettet med det nye system",
    deleteKey: null,
    deleteLabel: "",
    confirmText: "",
  },
  {
    label: "Produkter",
    key: "products",
    description: "Produktposter i databasen",
    deleteKey: "deleteProducts",
    deleteLabel: "Slet alle produkter",
    confirmText: "Slet ALLE produkter inkl. snapshots?\n\nHandlingen kan ikke fortrydes.",
  },
  {
    label: "Prishistorik (v1)",
    key: "price_history_v1",
    description: "Prispunkter fra det gamle system",
    deleteKey: "deletePriceHistory",
    deleteLabel: "Slet al prishistorik",
    confirmText: "Slet AL prishistorik (v1 + v2 price events + source checks)?\n\nHandlingen kan ikke fortrydes.",
  },
  {
    label: "Prisevents (v2)",
    key: "price_events_v2",
    description: "Prispunkter fra det nye system",
    deleteKey: null,
    deleteLabel: "",
    confirmText: "",
  },
  {
    label: "Source checks",
    key: "source_checks",
    description: "Scrapning-logposter",
    deleteKey: null,
    deleteLabel: "",
    confirmText: "",
  },
  {
    label: "AI Jobs",
    key: "ai_jobs",
    description: "Ollama AI-analyser",
    deleteKey: "deleteAiJobs",
    deleteLabel: "Slet alle AI jobs",
    confirmText: "Slet ALLE AI jobs og LLM-analyseresultater?\n\nHandlingen kan ikke fortrydes.",
  },
  {
    label: "Email-kø",
    key: "email_queue",
    description: "Ventende emails",
    deleteKey: "deleteEmailQueue",
    deleteLabel: "Tøm email-kø",
    confirmText: "Tøm email-køen (slet alle ventende emails)?\n\nHandlingen kan ikke fortrydes.",
  },
];

export default function AdminDataPage() {
  const queryClient = useQueryClient();

  const { data: stats, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["admin", "data", "stats"],
    queryFn: () => api.adminData.stats(),
    refetchOnWindowFocus: false,
  });

  const makeMutation = (fn: () => Promise<unknown>) =>
    useMutation({
      mutationFn: fn,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["admin", "data", "stats"] });
        queryClient.invalidateQueries({ queryKey: ["watches"] });
        queryClient.invalidateQueries({ queryKey: ["products"] });
      },
    });

  const deleteWatches = makeMutation(() => api.adminData.deleteWatches());
  const deleteProducts = makeMutation(() => api.adminData.deleteProducts());
  const deletePriceHistory = makeMutation(() => api.adminData.deletePriceHistory());
  const deleteAiJobs = makeMutation(() => api.adminData.deleteAiJobs());
  const deleteEmailQueue = makeMutation(() => api.adminData.deleteEmailQueue());

  const mutations: Record<string, ReturnType<typeof makeMutation>> = {
    deleteWatches,
    deleteProducts,
    deletePriceHistory,
    deleteAiJobs,
    deleteEmailQueue,
  };

  function handleDelete(row: StatRow) {
    if (!row.deleteKey) return;
    if (!window.confirm(row.confirmText)) return;
    mutations[row.deleteKey].mutate();
  }

  return (
    <AuthGuard adminOnly>
      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Datahåndtering</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Overblik over systemdata og mulighed for sletning
            </p>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Opdater
          </button>
        </div>

        <div className="rounded-lg border border-slate-800 overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Datatype</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider w-24">Antal</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider w-48"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {rows.map((row) => {
                  const count = stats?.[row.key] ?? 0;
                  const mut = row.deleteKey ? mutations[row.deleteKey] : null;
                  const isPending = mut?.isPending ?? false;
                  return (
                    <tr key={row.key} className="hover:bg-slate-900/30">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-200">{row.label}</div>
                        <div className="text-xs text-slate-500">{row.description}</div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-300">
                        {count.toLocaleString("da-DK")}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {row.deleteKey && (
                          <button
                            onClick={() => handleDelete(row)}
                            disabled={isPending || count === 0}
                            className="inline-flex items-center gap-1.5 rounded-md bg-red-900/40 border border-red-800/50 px-2.5 py-1 text-xs font-medium text-red-400 hover:bg-red-900/70 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            {isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Trash2 className="h-3 w-3" />
                            )}
                            {row.deleteLabel}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="rounded-lg border border-slate-700 bg-amber-950/20 border-amber-800/30 p-4 text-sm text-amber-400">
          <strong>Bemærk:</strong> Sletning af watches inkluderer automatisk al tilhørende prishistorik (v1 + v2).
          Brug kun sletning til at rydde op — handlingerne kan ikke fortrydes.
        </div>
      </div>
    </AuthGuard>
  );
}
