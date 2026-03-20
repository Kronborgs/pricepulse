import { cn } from "@/lib/utils";
import { WatchStatus } from "@/types";

const STATUS_CONFIG: Record<
  WatchStatus,
  { label: string; class: string }
> = {
  pending:  { label: "Afventer",   class: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400" },
  active:   { label: "Aktiv",      class: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400" },
  paused:   { label: "Pauset",     class: "bg-slate-100 text-slate-600 dark:bg-slate-900/20 dark:text-slate-400" },
  error:    { label: "Fejl",       class: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400" },
  blocked:  { label: "Blokeret",   class: "bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400" },
};

export function StatusBadge({ status }: { status: WatchStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        cfg.class
      )}
    >
      {cfg.label}
    </span>
  );
}
