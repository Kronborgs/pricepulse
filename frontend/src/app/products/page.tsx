"use client";

import { useQuery } from "@tanstack/react-query";
import { Package2, Search, Users } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Product } from "@/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { UserFilterDropdown } from "@/components/ui/user-filter-dropdown";

function wordSimilarity(a: string, b: string): number {
  const words = (s: string) =>
    new Set(s.toLowerCase().replace(/[^a-z0-9æøå ]/g, " ").split(/\s+/).filter(Boolean));
  const wa = words(a);
  const wb = words(b);
  const intersection = Array.from(wa).filter((w) => wb.has(w)).length;
  return intersection / Math.max(wa.size, wb.size, 1);
}

function findDuplicatePairs(products: Product[]): [Product, Product][] {
  const pairs: [Product, Product][] = [];
  for (let i = 0; i < products.length; i++) {
    for (let j = i + 1; j < products.length; j++) {
      if (wordSimilarity(products[i].name, products[j].name) >= 0.45) {
        pairs.push([products[i], products[j]]);
      }
    }
  }
  return pairs.slice(0, 5); // vis max 5 forslag
}

export default function ProductsPage() {
  const { data: me } = useCurrentUser();
  const isPrivileged = me?.role === "admin" || me?.role === "superuser";

  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);

  // Hent brugerliste til filterdropdown (kun for admin/superuser)
  const { data: usersData } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.adminUsers.list({ limit: 100 }),
    enabled: isPrivileged,
  });

  // For duplicate detection we always load all products (no pagination filter)
  const { data: allData } = useQuery({
    queryKey: ["products-all-for-dups"],
    queryFn: () => api.products.list({ limit: 200 }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["products", { search, page, ownerFilter }],
    queryFn: () =>
      api.products.list({
        search: search || undefined,
        skip: (page - 1) * 24,
        limit: 24,
        owner_ids: ownerFilter.length ? ownerFilter : undefined,
      }),
  });

  const products: Product[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 24));

  const duplicatePairs = useMemo(
    () => findDuplicatePairs(allData?.items ?? []),
    [allData]
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Produkter</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} produkter i databasen
          </p>
        </div>
        {isPrivileged && (
          <UserFilterDropdown
            users={usersData?.items ?? []}
            selected={ownerFilter}
            onChange={(ids) => { setOwnerFilter(ids); setPage(1); }}
          />
        )}
      </div>

      {/* Duplicate suggestions */}
      {duplicatePairs.length > 0 && !search && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 space-y-2">
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            {duplicatePairs.length} mulig{duplicatePairs.length !== 1 ? "e dubletter" : " dublet"} fundet
          </p>
          <div className="space-y-1.5">
            {duplicatePairs.map(([a, b]) => (
              <div key={`${a.id}-${b.id}`} className="flex items-center gap-2 text-sm flex-wrap">
                <Link href={`/products/${a.id}`} className="text-amber-800 dark:text-amber-300 hover:underline font-medium truncate max-w-[200px]">
                  {a.name}
                </Link>
                <span className="text-amber-600 dark:text-amber-500">↔</span>
                <Link href={`/products/${b.id}`} className="text-amber-800 dark:text-amber-300 hover:underline font-medium truncate max-w-[200px]">
                  {b.name}
                </Link>
                <Link
                  href={`/products/${a.id}`}
                  className="ml-auto shrink-0 text-xs text-amber-700 dark:text-amber-400 hover:underline"
                >
                  Sammenflet →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative w-72">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="search"
          placeholder="Søg på navn eller brand…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
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
            <ProductCard key={product.id} product={product} showOwner={isPrivileged} />
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

function ProductCard({ product, showOwner }: { product: Product; showOwner?: boolean }) {
  return (
    <Link
      href={`/products/${product.id}`}
      className="group rounded-lg border border-border bg-card overflow-hidden hover:shadow-md transition-shadow"
    >
      {showOwner && product.owner_name && (
        <div className="px-3 pt-2.5 pb-0">
          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400">
            <Users className="h-3 w-3" />{product.owner_name}
          </span>
        </div>
      )}
      <div className="aspect-square bg-muted/20 flex items-center justify-center overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-contain p-3 group-hover:scale-105 transition-transform"
          />
        ) : (
          <img src="/logo.png" alt="PricePulse" className="h-24 w-24 object-contain opacity-60" />
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
