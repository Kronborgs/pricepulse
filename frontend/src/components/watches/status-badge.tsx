import { cn } from "@/lib/utils";
import { ProductWatchStatus, SourceStatus, WatchStatus } from "@/types";

type AnyStatus = WatchStatus | ProductWatchStatus | SourceStatus;

const STATUS_CONFIG: Record<AnyStatus, { label: string; class: string; pulse?: boolean }> = {
  pending:   { label: "Afventer",        class: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400" },
  active:    { label: "Aktiv",           class: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400" },
  paused:    { label: "Pauset",          class: "bg-slate-100 text-slate-600 dark:bg-slate-900/20 dark:text-slate-400" },
  error:     { label: "Fejl",            class: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400" },
  blocked:   { label: "Blokeret",        class: "bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400" },
  partial:   { label: "Delvist",         class: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400" },
  archived:  { label: "Arkiveret",       class: "bg-zinc-100 text-zinc-500 dark:bg-zinc-900/20 dark:text-zinc-500" },
  analysing: { label: "AI analyserer",   class: "bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400", pulse: true },
};

export function StatusBadge({ status }: { status: AnyStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        cfg.class,
        cfg.pulse && "animate-pulse"
      )}
    >
      {cfg.pulse && <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-ping" />}
      {cfg.label}
    </span>
  );
}
