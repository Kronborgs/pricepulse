"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, LineChart } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatPrice, formatRelative } from "@/lib/utils";
import { Watch } from "@/types";

interface StoreComparisonProps {
  productId: string;
  watches?: Watch[]; // kan sendes udefra for at undgå dobbelt fetch
}

export function StoreComparison({ productId, watches: watchesProp }: StoreComparisonProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["product-watches", productId],
    queryFn: () => api.watches.list({ product_id: productId }),
    enabled: !watchesProp, // hent kun hvis ingen watches er givet
  });

  if (!watchesProp && isLoading) {
    return <p className="text-sm text-muted-foreground">Indlæser butikker…</p>;
  }

  const watches: Watch[] = watchesProp ?? data?.items ?? [];

  if (watches.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Ingen butikker overvåges for dette produkt
      </p>
    );
  }

  const prices = watches
    .map((w) => w.current_price)
    .filter((p): p is number => p != null);
  const minPrice = prices.length > 0 ? Math.min(...prices) : null;

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">
              Butik
            </th>
            <th className="px-4 py-3 text-right font-medium text-muted-foreground">
              Pris
            </th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">
              Lager
            </th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">
              Tjekket
            </th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {watches.map((watch) => {
            const isCheapest =
              minPrice != null && watch.current_price === minPrice;
            return (
              <tr
                key={watch.id}
                className={`transition-colors hover:bg-slate-800/50 ${
                  isCheapest ? "bg-[#8DC63F]/5" : ""
                }`}
              >
                <td className="px-4 py-3">
                  <span className="font-medium">
                    {watch.shop?.name ?? watch.url}
                  </span>
                  {isCheapest && (
                    <span className="ml-2 rounded-full bg-[#8DC63F]/15 px-1.5 py-0.5 text-xs font-medium text-[#8DC63F]">
                      Billigst
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right tabular-nums font-medium">
                  {watch.current_price != null
                    ? formatPrice(watch.current_price)
                    : "—"}
                </td>
                <td className="px-4 py-3">
                  <StockBadge status={watch.current_stock_status} />
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {watch.last_checked_at
                    ? formatRelative(watch.last_checked_at)
                    : "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 justify-end">
                    <Link
                      href={`/watches/${watch.id}`}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      title="Se graf og diagnostik"
                    >
                      <LineChart className="h-3.5 w-3.5" />
                    </Link>
                    <Link
                      href={watch.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      title="Åbn i butik"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StockBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  const label =
    status === "in_stock"
      ? "På lager"
      : status === "out_of_stock"
      ? "Udsolgt"
      : status === "preorder"
      ? "Forudbestilling"
      : status;
  const cls =
    status === "in_stock"
      ? "text-green-600"
      : status === "out_of_stock"
      ? "text-red-500"
      : "text-muted-foreground";
  return <span className={`text-xs font-medium ${cls}`}>{label}</span>;
}
