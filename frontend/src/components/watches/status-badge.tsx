import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { ProductWatchStatus, SourceStatus, WatchStatus } from "@/types";

type AnyStatus = WatchStatus | ProductWatchStatus | SourceStatus;

const STATUS_CLASSES: Record<AnyStatus, { class: string; pulse?: boolean }> = {
  pending:      { class: "bg-yellow-900/20 text-yellow-400" },
  active:       { class: "bg-[#8DC63F]/15 text-[#8DC63F]" },
  paused:       { class: "bg-slate-800 text-slate-400" },
  error:        { class: "bg-red-900/20 text-red-400" },
  blocked:      { class: "bg-orange-900/20 text-orange-400" },
  partial:      { class: "bg-blue-900/20 text-blue-400" },
  archived:     { class: "bg-zinc-900/20 text-zinc-500" },
  ai_analyzing: { class: "bg-purple-900/20 text-purple-400", pulse: true },
  ai_active:    { class: "bg-purple-900/20 text-purple-400" },
};

export function StatusBadge({ status }: { status: AnyStatus }) {
  const { t } = useI18n();
  const statusKeyMap: Record<AnyStatus, string> = {
    pending:      t("status_pending"),
    active:       t("status_active"),
    paused:       t("status_paused"),
    error:        t("status_error"),
    blocked:      t("status_blocked"),
    partial:      t("status_partial"),
    archived:     t("status_archived"),
    ai_analyzing: t("status_ai_analyzing"),
    ai_active:    t("status_ai_active"),
  };
  const cfg = STATUS_CLASSES[status] ?? STATUS_CLASSES.pending;
  const label = statusKeyMap[status] ?? status;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        cfg.class,
        cfg.pulse && "animate-pulse"
      )}
    >
      {cfg.pulse && <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-ping" />}
      {label}
    </span>
  );
}
