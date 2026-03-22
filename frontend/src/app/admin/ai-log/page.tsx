"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { AIJob } from "@/types";
import { Loader2, RefreshCw, XCircle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { da } from "date-fns/locale";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-slate-500/20 text-slate-400",
  processing: "bg-blue-500/20 text-blue-400",
  completed: "bg-green-500/20 text-green-400",
  failed: "bg-red-500/20 text-red-400",
  cancelled: "bg-yellow-500/20 text-yellow-400",
};

const TYPE_LABELS: Record<string, string> = {
  parser_advice: "Parser-råd",
  normalization: "Normalisering",
  product_matching: "Produktmatch",
  selector_suggest: "Selector-forslag",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? "bg-slate-500/20 text-slate-400"}`}
    >
      {status}
    </span>
  );
}

export default function AILogPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [selected, setSelected] = useState<AIJob | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["ai", "jobs", statusFilter, typeFilter],
    queryFn: () =>
      api.aiJobs.list({
        status: statusFilter || undefined,
        job_type: typeFilter || undefined,
        limit: 50,
      }),
    refetchInterval: 15_000,
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.aiJobs.cancel(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai", "jobs"] }),
  });

  const jobs = data?.items ?? [];

  return (
    <AuthGuard adminOnly>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Job Log</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Alle Ollama-kald — permanent auditlog
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-white/5"
          >
            <RefreshCw className="h-4 w-4" />
            Opdater
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
          >
            <option value="">Alle typer</option>
            {Object.entries(TYPE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
          >
            <option value="">Alle statusser</option>
            {Object.keys(STATUS_COLORS).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
          </div>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-slate-500 py-8 text-center">Ingen jobs fundet</p>
        ) : (
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Type</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Model</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Varighed</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Startet</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="hover:bg-white/5 cursor-pointer"
                    onClick={() => setSelected(job)}
                  >
                    <td className="px-4 py-2.5 text-slate-200">
                      {TYPE_LABELS[job.job_type] ?? job.job_type}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-4 py-2.5 text-slate-400 font-mono text-xs">
                      {job.model_used ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400">
                      {job.duration_ms != null ? `${job.duration_ms} ms` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs">
                      {job.queued_at
                        ? formatDistanceToNow(new Date(job.queued_at), {
                            addSuffix: true,
                            locale: da,
                          })
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      {(job.status === "queued" || job.status === "processing") && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            cancelMutation.mutate(job.id);
                          }}
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Detail panel */}
        {selected && (
          <div
            className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
            onClick={() => setSelected(null)}
          >
            <div
              className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-2xl w-full space-y-4 mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">
                  {TYPE_LABELS[selected.job_type] ?? selected.job_type}
                </h2>
                <StatusBadge status={selected.status} />
              </div>
              {selected.summary && (
                <p className="text-sm text-slate-300">{selected.summary}</p>
              )}
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                <span>Model: {selected.model_used ?? "—"}</span>
                <span>Varighed: {selected.duration_ms != null ? `${selected.duration_ms} ms` : "—"}</span>
                {selected.source_id && <span>Source: {selected.source_id}</span>}
                {selected.watch_id && <span>Watch: {selected.watch_id}</span>}
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-sm text-slate-400 hover:text-slate-200"
              >
                Luk
              </button>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
