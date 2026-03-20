"use client";

import { useQuery } from "@tanstack/react-query";
import { Package2, Search } from "lucide-react";
import Link from "next/link";
import { useQueryState } from "nuqs";
import { useState } from "react";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Product } from "@/types";

export default function ProductsPage() {
  const [search, setSearch] = useQueryState("search", { defaultValue: "" });
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["products", { search, page }],
    queryFn: () =>
      api.products.list({
        search: search || undefined,
        skip: (page - 1) * 24,
        limit: 24,
      }),
  });

  const products: Product[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 24));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Produkter</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} produkter i databasen
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative w-72">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="search"
          placeholder="Søg på navn eller brand…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value || null);
            setPage(1);
          }}
          className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-48 rounded-lg border border-border bg-muted/30 animate-pulse"
            />
          ))}
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <Package2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Ingen produkter fundet</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md border px-3 py-1.5 disabled:opacity-40 hover:bg-muted transition-colors"
          >
            Forrige
          </button>
          <span className="text-muted-foreground">
            Side {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md border px-3 py-1.5 disabled:opacity-40 hover:bg-muted transition-colors"
          >
            Næste
          </button>
        </div>
      )}
    </div>
  );
}

function ProductCard({ product }: { product: Product }) {
  return (
    <Link
      href={`/products/${product.id}`}
      className="group rounded-lg border border-border bg-card overflow-hidden hover:shadow-md transition-shadow"
    >
      <div className="aspect-square bg-muted/20 flex items-center justify-center overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-contain p-3 group-hover:scale-105 transition-transform"
          />
        ) : (
          <Package2 className="h-12 w-12 text-muted-foreground/40" />
        )}
      </div>
      <div className="p-3">
        {product.brand && (
          <p className="text-xs text-muted-foreground mb-0.5">{product.brand}</p>
        )}
        <p className="text-sm font-medium line-clamp-2 leading-snug">
          {product.name}
        </p>
        {product.lowest_price != null && (
          <p className="mt-1.5 text-sm font-semibold text-green-600">
            Fra {formatPrice(product.lowest_price)}
          </p>
        )}
        {product.watch_count != null && product.watch_count > 0 && (
          <p className="text-xs text-muted-foreground mt-1">
            {product.watch_count} butik
            {product.watch_count !== 1 ? "ker" : ""}
          </p>
        )}
      </div>
    </Link>
  );
}
