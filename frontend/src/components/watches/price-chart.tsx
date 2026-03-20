"use client";

import { useQuery } from "@tanstack/react-query";
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
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";

interface Props {
  watchId: string;
  currency?: string;
}

export function PriceChart({ watchId, currency = "DKK" }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["price-history", watchId],
    queryFn: () => api.history.prices(watchId, { limit: 500 }),
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
        Indlæser prishistorik…
      </div>
    );
  }

  if (error || !data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
        Ingen prisdata endnu
      </div>
    );
  }

  const chartData = data
    .filter((p) => p.price != null)
    .map((p) => ({
      date: new Date(p.recorded_at).getTime(),
      price: Number(p.price),
      stock: p.stock_status,
    }));

  const prices = chartData.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.1 || 50;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
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
          tickFormatter={(v) => formatPrice(v, currency)}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          labelFormatter={(v) =>
            format(new Date(v as number), "d. MMM yyyy HH:mm", { locale: da })
          }
          formatter={(v: number) => [formatPrice(v, currency), "Pris"]}
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--card))",
            color: "hsl(var(--foreground))",
          }}
        />
        <Line
          type="stepAfter"
          dataKey="price"
          stroke="hsl(var(--chart-1))"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
