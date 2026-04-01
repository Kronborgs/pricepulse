"use client";

import { useCallback, useEffect, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format } from "date-fns";
import { da } from "date-fns/locale";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Watch, PriceHistoryPoint } from "@/types";

const COLORS = [
  "#29ABE2", "#F5A623", "#8DC63F", "#EF4444",
  "#A855F7", "#EC4899", "#14B8A6", "#F97316",
];

type TimeRange = "7d" | "30d" | "3m" | "all";
const RANGE_LABELS: Record<TimeRange, string> = {
  "7d": "7 dage",
  "30d": "30 dage",
  "3m": "3 mdr.",
  "all": "Alt",
};

interface Props {
  watches: Watch[];
  productId: string;
}

interface MergedPoint {
  date: number;
  [watchId: string]: number | null;
}

function mergeHistories(
  entries: { watchId: string; data: { recorded_at: string; price: number | null }[] }[]
): MergedPoint[] {
  if (entries.every((e) => e.data.length === 0)) return [];

  const allTs = new Set<number>();
  entries.forEach(({ data }) =>
    data.forEach((p) => allTs.add(new Date(p.recorded_at).getTime()))
  );

  const sorted = Array.from(allTs).sort((a, b) => a - b);

  return sorted.map((ts) => {
    const point: MergedPoint = { date: ts };
    entries.forEach(({ watchId, data }) => {
      let price: number | null = null;
      for (const p of data) {
        const t = new Date(p.recorded_at).getTime();
        if (t <= ts && p.price != null) price = p.price;
        else if (t > ts) break;
      }
      point[watchId] = price;
    });
    return point;
  });
}

/** Trim data to cutoff and carry the last known price forward as the first boundary point */
function applyTimeRange(
  entries: { watchId: string; label: string; data: PriceHistoryPoint[] }[],
  cutoffMs: number
) {
  if (cutoffMs === 0) return entries;
  return entries.map((e) => {
    const before = e.data.filter((p) => new Date(p.recorded_at).getTime() < cutoffMs);
    const after = e.data.filter((p) => new Date(p.recorded_at).getTime() >= cutoffMs);
    const lastBefore = before[before.length - 1];
    if (lastBefore) {
      return {
        ...e,
        data: [{ recorded_at: new Date(cutoffMs).toISOString(), price: lastBefore.price }, ...after],
      };
    }
    return { ...e, data: after };
  });
}

export function MultiPriceChart({ watches, productId }: Props) {
  const LS_HIDDEN = `chart_hidden_${productId}`;
  const LS_RANGE = `chart_range_${productId}`;

  const [hidden, setHidden] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set();
    try {
      const s = localStorage.getItem(LS_HIDDEN);
      return s ? new Set(JSON.parse(s)) : new Set();
    } catch { return new Set(); }
  });

  const [range, setRange] = useState<TimeRange>(() => {
    if (typeof window === "undefined") return "all";
    try { return (localStorage.getItem(LS_RANGE) as TimeRange) ?? "all"; }
    catch { return "all"; }
  });

  useEffect(() => {
    try { localStorage.setItem(LS_HIDDEN, JSON.stringify(Array.from(hidden))); }
    catch { /* ignore */ }
  }, [hidden, LS_HIDDEN]);

  useEffect(() => {
    try { localStorage.setItem(LS_RANGE, range); }
    catch { /* ignore */ }
  }, [range, LS_RANGE]);

  const toggleHidden = useCallback((wid: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(wid) ? next.delete(wid) : next.add(wid);
      return next;
    });
  }, []);

  const results = useQueries({
    queries: watches.map((w) => ({
      queryKey: ["price-history", w.id],
      queryFn: () => api.history.prices(w.id, { limit: 500 }),
      staleTime: 60_000,
    })),
  });

  const isLoading = results.some((r) => r.isLoading);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground text-sm gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Indlæser prishistorik…
      </div>
    );
  }

  const allEntries = watches.map((w, i) => ({
    watchId: w.id,
    label: w.shop?.name ?? w.title ?? w.url,
    color: COLORS[i % COLORS.length],
    currentPrice: w.current_price,
    data: (results[i].data ?? []).slice().sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    ),
  }));

  const hasData = allEntries.some((e) => e.data.length > 0);
  if (!hasData) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
        Ingen prishistorik endnu
      </div>
    );
  }

  const cutoffMs =
    range === "7d" ? Date.now() - 7 * 86_400_000 :
    range === "30d" ? Date.now() - 30 * 86_400_000 :
    range === "3m" ? Date.now() - 90 * 86_400_000 : 0;

  const rangedEntries = applyTimeRange(allEntries, cutoffMs);
  const visibleEntries = rangedEntries.filter((e) => !hidden.has(e.watchId));
  const merged = mergeHistories(
    visibleEntries as { watchId: string; data: { recorded_at: string; price: number | null }[] }[]
  );

  const allPrices = merged.flatMap((p) =>
    visibleEntries.map((e) => p[e.watchId]).filter((v): v is number => v != null)
  );
  const minPrice = allPrices.length ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length ? Math.max(...allPrices) : 100;
  const pad = (maxPrice - minPrice) * 0.08 || 50;
  const yMin = Math.max(0, Math.floor(minPrice - pad));
  const yMax = Math.ceil(maxPrice + pad);

  function xTickFormatter(v: number) {
    const d = new Date(v);
    const diffDays = (Date.now() - v) / 86_400_000;
    if (diffDays < 2) return format(d, "HH:mm", { locale: da });
    if (diffDays < 60) return format(d, "d. MMM", { locale: da });
    return format(d, "MMM yy", { locale: da });
  }

  return (
    <div className="space-y-3">
      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Time range selector */}
        <div className="flex rounded-md border border-border overflow-hidden text-xs shrink-0">
          {(["7d", "30d", "3m", "all"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1.5 font-medium transition-colors ${
                range === r
                  ? "bg-[#29ABE2] text-white"
                  : "bg-background text-muted-foreground hover:bg-muted"
              }`}
            >
              {RANGE_LABELS[r]}
            </button>
          ))}
        </div>

        {/* Shop toggle pills */}
        <div className="flex flex-wrap gap-1.5 ml-auto">
          {allEntries.map((e) => {
            const isHidden = hidden.has(e.watchId);
            return (
              <button
                key={e.watchId}
                onClick={() => toggleHidden(e.watchId)}
                title={isHidden ? "Vis linje" : "Skjul linje"}
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all ${
                  isHidden
                    ? "border-border text-muted-foreground opacity-40 hover:opacity-70"
                    : "border-transparent text-white"
                }`}
                style={!isHidden ? { backgroundColor: e.color } : undefined}
              >
                <span
                  className="inline-block w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: e.color }}
                />
                {e.label}
                {e.currentPrice != null && (
                  <span className="opacity-80">{formatPrice(e.currentPrice)}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart */}
      {merged.length === 0 ? (
        <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
          Ingen data i det valgte tidsrum
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={merged} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="date"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={xTickFormatter}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              minTickGap={60}
            />
            <YAxis
              domain={[yMin, yMax]}
              tickFormatter={(v) => formatPrice(v)}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={85}
            />
            <Tooltip
              labelFormatter={(v) =>
                format(new Date(v as number), "d. MMM yyyy HH:mm", { locale: da })
              }
              formatter={(v: number, name: string) => {
                const entry = allEntries.find((e) => e.watchId === name);
                return [formatPrice(v), entry?.label ?? name];
              }}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                background: "hsl(var(--card))",
                color: "hsl(var(--foreground))",
                fontSize: 12,
              }}
            />
            {visibleEntries.map((entry) => {
              const color = allEntries.find((e) => e.watchId === entry.watchId)?.color ?? "#29ABE2";
              return (
              <Line
                key={entry.watchId}
                type="stepAfter"
                dataKey={entry.watchId}
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            );
            })}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

