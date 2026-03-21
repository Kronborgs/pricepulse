"use client";

import Link from "next/link";
import { cn, formatPrice, getDomain } from "@/lib/utils";
import { WatchSource, SourceStatus } from "@/types";

const DOT_CLASS: Record<SourceStatus, string> = {
  active:       "bg-green-500",
  pending:      "bg-yellow-400",
  paused:       "bg-slate-400",
  error:        "bg-red-500",
  blocked:      "bg-orange-500",
  archived:     "bg-zinc-400",
  ai_analyzing: "bg-purple-400",
  ai_active:    "bg-purple-500",
};

interface Props {
  source: WatchSource;
  /** Whether this is the source with the best (lowest) price */
  isBest?: boolean;
}

export function SourceStatusPill({ source, isBest }: Props) {
  const dotClass = DOT_CLASS[source.status] ?? DOT_CLASS.pending;
  const domain = getDomain(source.url);

  return (
    <Link
      href={`/sources/${source.id}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors hover:bg-accent",
        isBest ? "border-green-500/40 bg-green-50 dark:bg-green-950/20" : "border-border bg-card"
      )}
      title={`${domain} — ${source.status}`}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full flex-shrink-0", dotClass)} />
      <span className="truncate max-w-[120px]">{domain}</span>
      {source.last_price != null && (
        <span className={cn("font-medium tabular-nums", isBest ? "text-green-700 dark:text-green-400" : "")}>
          {formatPrice(source.last_price, source.last_currency)}
        </span>
      )}
    </Link>
  );
}
