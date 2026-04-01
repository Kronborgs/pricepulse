"use client";

import { useCallback, useEffect, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format } from "date-fns";
import { da } from "date-fns/locale";
import { Loader2, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Watch, PriceHistoryPoint } from "@/types";

// ─── Palette — vibrant on dark navy ──────────────────────────────────────────
const PALETTE = [
  "#60A5FA", // blue-400
  "#FB923C", // orange-400
  "#4ADE80", // green-400
  "#F472B6", // pink-400
  "#A78BFA", // violet-400
  "#22D3EE", // cyan-400
  "#FBBF24", // amber-400
  "#F87171", // red-400
];

type TimeRange = "7d" | "30d" | "3m" | "all";

const RANGES: { key: TimeRange; label: string }[] = [
  { key: "7d", label: "7 dage" },
  { key: "30d", label: "30 dage" },
  { key: "3m", label: "3 mdr." },
  { key: "all", label: "Alt" },
];

interface Props {
  watches: Watch[];
  productId: string;
}

interface ChartEntry {
  watchId: string;
  label: string;
  color: string;
  currentPrice: number | null;
  data: PriceHistoryPoint[];
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
function applyTimeRange(entries: ChartEntry[], cutoffMs: number): ChartEntry[] {
  if (cutoffMs === 0) return entries;
  return entries.map((e) => {
    const before = e.data.filter((p) => new Date(p.recorded_at).getTime() < cutoffMs);
    const after = e.data.filter((p) => new Date(p.recorded_at).getTime() >= cutoffMs);
    const lastBefore = before[before.length - 1];
    if (lastBefore) {
      return {
        ...e,
        data: [
          {
            recorded_at: new Date(cutoffMs).toISOString(),
            price: lastBefore.price,
            stock_status: lastBefore.stock_status,
            is_change: false,
          } as PriceHistoryPoint,
          ...after,
        ],
      };
    }
    return { ...e, data: after };
  });
}

/** IQR-based domain — outliers don't destroy y-axis readability */
function smartDomain(prices: number[]): [number, number] {
  if (prices.length === 0) return [0, 1000];
  if (prices.length < 4) {
    const mn = Math.min(...prices);
    const mx = Math.max(...prices);
    const pad = (mx - mn) * 0.12 || 50;
    return [Math.max(0, Math.floor(mn - pad)), Math.ceil(mx + pad)];
  }
  const s = [...prices].sort((a, b) => a - b);
  const q1 = s[Math.floor(s.length * 0.25)];
  const q3 = s[Math.floor(s.length * 0.75)];
  const iqr = q3 - q1;
  const clipped = prices.filter((p) => p >= q1 - 2.5 * iqr && p <= q3 + 2.5 * iqr);
  const mn = Math.min(...clipped);
  const mx = Math.max(...clipped);
  const pad = (mx - mn) * 0.1 || 50;
  return [Math.max(0, Math.floor(mn - pad)), Math.ceil(mx + pad)];
}

function xTickFmt(v: number, diffMs: number): string {
  const d = new Date(v);
  if (diffMs <= 2 * 86_400_000) return format(d, "HH:mm", { locale: da });
  if (diffMs <= 60 * 86_400_000) return format(d, "d. MMM", { locale: da });
  return format(d, "MMM yy", { locale: da });
}

function yTickFmt(v: number): string {
  if (v >= 10_000) return `${Math.round(v / 1000)}k`;
  if (v >= 1_000) return `${(v / 1000).toFixed(1).replace(".", ",")}k`;
  return String(Math.round(v));
}

// ─── Custom dark-glass tooltip ────────────────────────────────────────────────
function ChartTooltip({
  active,
  payload,
  label,
  entries,
}: {
  active?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: any[];
  label?: number;
  entries: ChartEntry[];
}) {
  if (!active || !payload?.length || label == null) return null;
  const items = entries
    .map((e) => ({ ...e, price: payload.find((p) => p.dataKey === e.watchId)?.value ?? null }))
    .filter((e) => e.price != null)
    .sort((a, b) => (a.price as number) - (b.price as number));
  if (items.length === 0) return null;
  const lowest = items[0];
  return (
    <div className="rounded-xl border border-white/10 bg-[#0d1526]/95 shadow-2xl backdrop-blur-sm p-3 min-w-[190px]">
      <p className="text-[11px] text-slate-400 mb-2.5 font-medium">
        {format(new Date(label), "d. MMM yyyy  HH:mm", { locale: da })}
      </p>
      <div className="space-y-1.5">
        {items.map((item) => {
          const isCheapest = item.watchId === lowest.watchId;
          return (
            <div key={item.watchId} className="flex items-center justify-between gap-5">
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className={`text-xs truncate ${isCheapest ? "text-white font-medium" : "text-slate-300"}`}>
                  {item.label}
                </span>
              </div>
              <span className={`text-xs font-semibold tabular-nums whitespace-nowrap ${isCheapest ? "text-emerald-400" : "text-slate-200"}`}>
                {formatPrice(item.price)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
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
      <div className="flex h-64 items-center justify-center text-slate-400 text-sm gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Indlæser prishistorik…
      </div>
    );
  }

  const allEntries: ChartEntry[] = watches.map((w, i) => ({
    watchId: w.id,
    label: w.shop?.name ?? w.title ?? w.url,
    color: PALETTE[i % PALETTE.length],
    currentPrice: w.current_price ?? null,
    data: (results[i].data ?? []).slice().sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    ),
  }));

  if (!allEntries.some((e) => e.data.length > 0)) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-500 text-sm">
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
  const [yMin, yMax] = smartDomain(allPrices);

  const tsDiff =
    merged.length >= 2 ? merged[merged.length - 1].date - merged[0].date : 86_400_000;

  const cheapest =
    allEntries
      .filter((e) => !hidden.has(e.watchId) && e.currentPrice != null)
      .sort((a, b) => (a.currentPrice ?? Infinity) - (b.currentPrice ?? Infinity))[0] ?? null;

  return (
    <div className="space-y-4">
      {/* ── Controls ── */}
      <div className="flex flex-wrap items-start gap-3">
        {/* Period tabs */}
        <div className="flex rounded-lg overflow-hidden bg-white/5 p-0.5 gap-0.5">
          {RANGES.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setRange(key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                range === key
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Store chips */}
        <div className="flex flex-wrap gap-1.5 ml-auto">
          {allEntries.map((e) => {
            const isHidden = hidden.has(e.watchId);
            return (
              <button
                key={e.watchId}
                onClick={() => toggleHidden(e.watchId)}
                title={isHidden ? "Vis" : "Skjul"}
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all cursor-pointer"
                style={
                  isHidden
                    ? {
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        color: "#475569",
                      }
                    : {
                        background: `${e.color}1a`,
                        border: `1px solid ${e.color}40`,
                        color: e.color,
                      }
                }
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: isHidden ? "#475569" : e.color }}
                />
                {e.label}
                {!isHidden && e.currentPrice != null && (
                  <span className="opacity-70 tabular-nums">{formatPrice(e.currentPrice)}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Cheapest-now banner ── */}
      {cheapest && (
        <div
          className="flex items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-sm"
          style={{
            background: `linear-gradient(90deg, ${cheapest.color}14 0%, transparent 100%)`,
            borderLeft: `3px solid ${cheapest.color}80`,
          }}
        >
          <TrendingDown className="h-3.5 w-3.5 shrink-0" style={{ color: cheapest.color }} />
          <span className="text-slate-400 text-xs">
            Billigst nu:{" "}
            <span className="font-semibold text-white">{cheapest.label}</span>
          </span>
          <span
            className="ml-auto font-bold tabular-nums text-sm"
            style={{ color: cheapest.color }}
          >
            {formatPrice(cheapest.currentPrice)}
          </span>
        </div>
      )}

      {/* ── Chart ── */}
      {merged.length === 0 ? (
        <div className="flex h-52 items-center justify-center text-slate-500 text-sm">
          Ingen data i det valgte tidsrum
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={290}>
          <AreaChart data={merged} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
            <defs>
              {visibleEntries.map((e) => (
                <linearGradient key={e.watchId} id={`grad-${e.watchId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor={e.color} stopOpacity={0.20} />
                  <stop offset="60%"  stopColor={e.color} stopOpacity={0.06} />
                  <stop offset="100%" stopColor={e.color} stopOpacity={0.00} />
                </linearGradient>
              ))}
            </defs>

            <CartesianGrid
              strokeDasharray="2 4"
              stroke="rgba(255,255,255,0.05)"
              vertical={false}
            />

            <XAxis
              dataKey="date"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => xTickFmt(v, tsDiff)}
              tick={{ fontSize: 11, fill: "#475569" }}
              tickLine={false}
              axisLine={false}
              minTickGap={64}
            />

            <YAxis
              domain={[yMin, yMax]}
              tickFormatter={yTickFmt}
              tick={{ fontSize: 11, fill: "#475569" }}
              tickLine={false}
              axisLine={false}
              width={44}
            />

            <Tooltip
              content={(props) => (
                <ChartTooltip
                  {...props}
                  entries={allEntries.filter((e) => !hidden.has(e.watchId))}
                />
              )}
              cursor={{
                stroke: "rgba(255,255,255,0.08)",
                strokeWidth: 1,
                strokeDasharray: "4 4",
              }}
            />

            {visibleEntries.map((e) => (
              <Area
                key={e.watchId}
                type="stepAfter"
                dataKey={e.watchId}
                stroke={e.color}
                strokeWidth={2}
                fill={`url(#grad-${e.watchId})`}
                dot={false}
                activeDot={{
                  r: 4,
                  fill: e.color,
                  stroke: "rgba(0,0,0,0.5)",
                  strokeWidth: 2,
                }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

