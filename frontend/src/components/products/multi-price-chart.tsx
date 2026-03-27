"use client";

import { useQueries } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
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

// Farvepalet — én farve pr. butik
const COLORS = [
  "#29ABE2", "#F5A623", "#8DC63F", "#EF4444",
  "#A855F7", "#EC4899", "#14B8A6", "#F97316",
];

interface Props {
  watches: Watch[];
}

interface MergedPoint {
  date: number;
  [watchId: string]: number | null;
}

/**
 * Fletter prishistorik fra flere watches til ét fælles datasæt.
 * For hvert tidspunkt tildeles alle watches den seneste pris op til det tidspunkt (step-after).
 */
function mergeHistories(
  entries: { watchId: string; data: PriceHistoryPoint[] }[]
): MergedPoint[] {
  if (entries.every((e) => e.data.length === 0)) return [];

  // Saml alle unikke tidspunkter
  const allTs = new Set<number>();
  entries.forEach(({ data }) => {
    data.forEach((p) => allTs.add(new Date(p.recorded_at).getTime()));
  });

  const sorted = Array.from(allTs).sort((a, b) => a - b);

  return sorted.map((ts) => {
    const point: MergedPoint = { date: ts };
    entries.forEach(({ watchId, data }) => {
      // Seneste pris ≤ dette tidspunkt
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

export function MultiPriceChart({ watches }: Props) {
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

  const entries = watches.map((w, i) => ({
    watchId: w.id,
    label: w.shop?.name ?? w.title ?? w.url,
    data: (results[i].data ?? []).slice().sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    ),
  }));

  const hasData = entries.some((e) => e.data.length > 0);
  if (!hasData) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
        Ingen prishistorik endnu
      </div>
    );
  }

  const merged = mergeHistories(entries);

  const allPrices = merged.flatMap((p) =>
    watches.map((w) => p[w.id]).filter((v): v is number => v != null)
  );
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const padding = (maxPrice - minPrice) * 0.1 || 50;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart
        data={merged}
        margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis
          dataKey="date"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(v) => format(new Date(v), "d. MMM", { locale: da })}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[minPrice - padding, maxPrice + padding]}
          tickFormatter={(v) => formatPrice(v)}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          labelFormatter={(v) =>
            format(new Date(v as number), "d. MMM yyyy HH:mm", { locale: da })
          }
          formatter={(v: number, name: string) => {
            const entry = entries.find((e) => e.watchId === name);
            return [formatPrice(v), entry?.label ?? name];
          }}
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--card))",
            color: "hsl(var(--foreground))",
          }}
        />
        <Legend
          formatter={(value) => {
            const entry = entries.find((e) => e.watchId === value);
            return entry?.label ?? value;
          }}
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
        />
        {entries.map((entry, i) => (
          <Line
            key={entry.watchId}
            type="stepAfter"
            dataKey={entry.watchId}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
