"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatPrice, formatRelative } from "@/lib/utils";
import { PriceEvent } from "@/types";
import { useI18n } from "@/lib/i18n";

export function RecentChanges({ ownerId }: { ownerId?: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["recent-events", ownerId],
    queryFn: () => api.dashboard.recentEvents(20, ownerId),
    refetchInterval: 30_000,
  });
  const { t, locale } = useI18n();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <h2 className="text-base font-semibold mb-4">{t("recent_changes_title")}</h2>
        <p className="text-sm text-muted-foreground">{t("recent_changes_loading")}</p>
      </div>
    );
  }

  const events = data ?? [];

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-semibold">{t("recent_changes_title")}</h2>
      </div>

      {events.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted-foreground">
          {t("recent_changes_empty")}
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {events.map((event) => (
            <EventRow key={event.id} event={event} locale={locale} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EventRow({ event, locale }: { event: PriceEvent; locale: string }) {
  const isDrop = (event.price_delta ?? 0) < 0;
  const isRise = (event.price_delta ?? 0) > 0;
  const displayName = event.watch_title ?? `Watch ${event.watch_id.slice(0, 8)}…`;

  return (
    <li className="flex items-center gap-3 px-5 py-3 hover:bg-muted/20 transition-colors">
      {/* Product thumbnail */}}
      <div className="flex-shrink-0 w-9 h-9 rounded-md overflow-hidden bg-muted border border-border">
        {event.watch_image_url ? (
          <img
            src={event.watch_image_url}
            alt={displayName}
            className="w-full h-full object-contain"
            loading="lazy"
            onError={(e) => {
              const el = e.currentTarget as HTMLImageElement;
              el.onerror = null;
              el.src = "/logo.png";
              el.className = "w-full h-full object-contain p-1 opacity-60";
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div
              className={`rounded-full p-1 ${
                isDrop
                  ? "bg-green-900/40 text-[#8DC63F]"
                  : isRise
                  ? "bg-red-900/40 text-red-400"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {isDrop ? (
                <ArrowDown className="h-3 w-3" />
              ) : isRise ? (
                <ArrowUp className="h-3 w-3" />
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* Arrow indicator (only shown when image is present) */}}
      {event.watch_image_url && (
        <div
          className={`flex-shrink-0 rounded-full p-1.5 ${
            isDrop
              ? "bg-green-900/30 text-[#8DC63F]"
              : isRise
              ? "bg-red-900/30 text-red-400"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {isDrop ? (
            <ArrowDown className="h-3.5 w-3.5" />
          ) : isRise ? (
            <ArrowUp className="h-3.5 w-3.5" />
          ) : null}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <Link
          href={`/watches/${event.watch_id}`}
          className="text-sm font-medium hover:underline truncate block"
        >
          {displayName}
        </Link>
        <p className="text-xs text-muted-foreground">
          {event.event_type === "price_change"
            ? `${formatPrice(event.old_price, "DKK", locale)} → ${formatPrice(event.new_price, "DKK", locale)}`
            : event.event_type === "stock_change"
            ? `${event.old_stock} → ${event.new_stock}`
            : event.event_type}
        </p>
      </div>

      <div className="text-right">
        {event.price_delta != null && (
          <p
            className={`text-sm font-medium tabular-nums ${
              isDrop ? "text-green-600" : isRise ? "text-red-500" : ""
            }`}
          >
            {isDrop ? "" : "+"}
            {formatPrice(event.price_delta, "DKK", locale)}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          {formatRelative(event.occurred_at, locale)}
        </p>
      </div>
    </li>
  );
}
