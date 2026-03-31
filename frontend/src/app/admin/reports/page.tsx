"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ExternalLink,
  Flag,
  Loader2,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { ScraperReport } from "@/types";
import { formatRelative } from "@/lib/utils";

const STATUS_TABS = [
  { value: "", label: "Alle" },
  { value: "new", label: "Nye" },
  { value: "read", label: "Læst" },
  { value: "resolved", label: "Løst" },
];

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  new: { label: "Ny", className: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
  read: { label: "Læst", className: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  resolved: { label: "Løst", className: "bg-green-500/20 text-green-400 border-green-500/30" },
};

export default function AdminReportsPage() {
  const [statusFilter, setStatusFilter] = useState("new");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-reports", statusFilter],
    queryFn: () => api.reports.list({ status: statusFilter || undefined }),
    refetchInterval: 30_000,
  });

  const reports = data?.items ?? [];
  const unread = data?.unread ?? 0;

  const markMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.reports.updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-reports"] });
      qc.invalidateQueries({ queryKey: ["reports-unread"] });
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Flag className="h-6 w-6 text-amber-400" />
            Scraper-rapporter
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Bruger-indsendte fejlrapporter for Data Webscraper
            {unread > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-semibold text-amber-400">
                {unread} ulæst{unread !== 1 ? "e" : ""}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border pb-0">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              statusFilter === tab.value
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
          <CheckCircle2 className="h-8 w-8 text-green-500/60" />
          <p className="text-sm">Ingen rapporter</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report: ScraperReport) => (
            <ReportCard
              key={report.id}
              report={report}
              onMark={(status) => markMutation.mutate({ id: report.id, status })}
              isUpdating={markMutation.isPending && markMutation.variables?.id === report.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ReportCard({
  report,
  onMark,
  isUpdating,
}: {
  report: ScraperReport;
  onMark: (status: string) => void;
  isUpdating: boolean;
}) {
  const badge = STATUS_BADGE[report.status] ?? STATUS_BADGE.new;

  return (
    <div className={`rounded-lg border bg-card p-4 space-y-3 transition-opacity ${isUpdating ? "opacity-50" : ""} ${report.status === "new" ? "border-amber-500/30" : "border-border"}`}>
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${badge.className}`}>
              {badge.label}
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(report.created_at).toLocaleString("da-DK")}
            </span>
            <span className="text-xs text-muted-foreground">
              fra{" "}
              <span className="font-medium text-foreground">
                {report.reporter.display_name ?? report.reporter.email}
              </span>
            </span>
          </div>

          {/* Watch link */}
          <div className="flex items-center gap-2">
            <Link
              href={`/watches/${report.watch_id}`}
              className="text-sm font-medium hover:underline text-primary truncate max-w-[360px]"
            >
              {report.watch.title ?? report.watch.url}
            </Link>
            <a
              href={report.watch.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          {report.status === "new" && (
            <button
              onClick={() => onMark("read")}
              disabled={isUpdating}
              className="rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-500/20 transition-colors disabled:opacity-50"
            >
              Markér læst
            </button>
          )}
          {report.status !== "resolved" && (
            <button
              onClick={() => onMark("resolved")}
              disabled={isUpdating}
              className="rounded-md border border-green-500/30 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5 inline mr-1" />
              Løst
            </button>
          )}
          {report.status === "resolved" && (
            <button
              onClick={() => onMark("new")}
              disabled={isUpdating}
              className="rounded-md border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors disabled:opacity-50"
            >
              Genåbn
            </button>
          )}
        </div>
      </div>

      {/* Comment */}
      {report.comment && (
        <div className="flex items-start gap-2 rounded-md bg-muted/40 px-3 py-2.5">
          <MessageSquare className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-sm text-foreground whitespace-pre-wrap">{report.comment}</p>
        </div>
      )}
    </div>
  );
}
