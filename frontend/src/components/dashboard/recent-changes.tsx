"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatPrice, formatRelative } from "@/lib/utils";
import { PriceEvent } from "@/types";

export function RecentChanges() {
  const { data, isLoading } = useQuery({
    queryKey: ["recent-events"],
    queryFn: () => api.dashboard.recentEvents(20),
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <h2 className="text-base font-semibold mb-4">Seneste ændringer</h2>
        <p className="text-sm text-muted-foreground">Indlæser…</p>
      </div>
    );
  }

  const events = data ?? [];

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-semibold">Seneste ændringer</h2>
      </div>

      {events.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted-foreground">
          Ingen ændringer endnu
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {events.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EventRow({ event }: { event: PriceEvent }) {
  const isDrop = (event.price_delta ?? 0) < 0;
  const isRise = (event.price_delta ?? 0) > 0;

  return (
    <li className="flex items-center gap-3 px-5 py-3 hover:bg-muted/20 transition-colors">
      <div
        className={`flex-shrink-0 rounded-full p-1.5 ${
          isDrop
            ? "bg-green-100 text-green-600 dark:bg-green-900/20"
            : isRise
            ? "bg-red-100 text-red-600 dark:bg-red-900/20"
            : "bg-muted text-muted-foreground"
        }`}
      >
        {isDrop ? (
          <ArrowDown className="h-3.5 w-3.5" />
        ) : isRise ? (
          <ArrowUp className="h-3.5 w-3.5" />
        ) : null}
      </div>

      <div className="flex-1 min-w-0">
        <Link
          href={`/watches/${event.watch_id}`}
          className="text-sm font-medium hover:underline truncate block"
        >
          Watch {event.watch_id.slice(0, 8)}…
        </Link>
        <p className="text-xs text-muted-foreground">
          {event.event_type === "price_change"
            ? `${formatPrice(event.old_price)} → ${formatPrice(event.new_price)}`
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
            {formatPrice(event.price_delta)}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          {formatRelative(event.occurred_at)}
        </p>
      </div>
    </li>
  );
}
