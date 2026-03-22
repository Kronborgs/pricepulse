import { cn } from "@/lib/utils";
import { ProductWatchStatus, SourceStatus, WatchStatus } from "@/types";

type AnyStatus = WatchStatus | ProductWatchStatus | SourceStatus;

const STATUS_CONFIG: Record<AnyStatus, { label: string; class: string; pulse?: boolean }> = {
  pending:   { label: "Afventer",        class: "bg-yellow-900/20 text-yellow-400" },
  active:    { label: "Aktiv",           class: "bg-[#8DC63F]/15 text-[#8DC63F]" },
  paused:    { label: "Pauset",          class: "bg-slate-800 text-slate-400" },
  error:     { label: "Fejl",            class: "bg-red-900/20 text-red-400" },
  blocked:   { label: "Blokeret",        class: "bg-orange-900/20 text-orange-400" },
  partial:   { label: "Delvist",         class: "bg-blue-900/20 text-blue-400" },
  archived:  { label: "Arkiveret",       class: "bg-zinc-900/20 text-zinc-500" },
  ai_analyzing: { label: "AI analyserer",   class: "bg-purple-900/20 text-purple-400", pulse: true },
  ai_active:    { label: "AI analyse",       class: "bg-purple-900/20 text-purple-400" },
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
