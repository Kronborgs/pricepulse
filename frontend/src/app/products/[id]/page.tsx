"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronLeft, ChevronRight, Loader2, Package2, Plus, Merge, Search, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { StoreComparison } from "@/components/products/store-comparison";
import { MultiPriceChart } from "@/components/products/multi-price-chart";
import { Product, Watch } from "@/types";
import { formatPrice } from "@/lib/utils";

// ─── Word-overlap similarity (0-1) ──────────────────────────────────────────
function similarity(a: string, b: string): number {
  const words = (s: string) =>
    new Set(s.toLowerCase().replace(/[^a-z0-9æøå ]/g, " ").split(/\s+/).filter(Boolean));
  const wa = words(a);
  const wb = words(b);
  const intersection = Array.from(wa).filter((w) => wb.has(w)).length;
  return intersection / Math.max(wa.size, wb.size, 1);
}

export default function ProductDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showAddStore, setShowAddStore] = useState(false);
  const [addUrl, setAddUrl] = useState("");
  const [addError, setAddError] = useState("");

  const [showMerge, setShowMerge] = useState(false);
  const [mergeSearch, setMergeSearch] = useState("");
  const [mergeTarget, setMergeTarget] = useState<Product | null>(null);

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.products.get(id),
  });

  const { data: watchesData } = useQuery({
    queryKey: ["product-watches", id],
    queryFn: () => api.watches.list({ product_id: id }),
    enabled: !!product,
  });
  const watches: Watch[] = watchesData?.items ?? [];

  // All products for prev/next navigation (reuses cache from the products list page)
  const { data: navProductsData } = useQuery({
    queryKey: ["products-all-for-dups"],
    queryFn: () => api.products.list({ limit: 200 }),
  });
  const navProducts = navProductsData?.items ?? [];
  const navIndex = navProducts.findIndex((p) => p.id === id);
  const prevId = navIndex > 0 ? navProducts[navIndex - 1].id : null;
  const nextId = navIndex >= 0 && navIndex < navProducts.length - 1 ? navProducts[navIndex + 1].id : null;

  // Load all products for the merge dialog (only when open)
  const { data: allProductsData } = useQuery({
    queryKey: ["products-all"],
    queryFn: () => api.products.list({ limit: 200 }),
    enabled: showMerge,
  });

  const otherProducts = useMemo(() => {
    if (!allProductsData || !product) return [];
    return allProductsData.items
      .filter((p) => p.id !== id)
      .map((p) => ({ ...p, score: similarity(p.name, product.name) }))
      .sort((a, b) => b.score - a.score);
  }, [allProductsData, product, id]);

  const filteredProducts = useMemo(() => {
    if (!mergeSearch.trim()) return otherProducts;
    const q = mergeSearch.toLowerCase();
    return otherProducts.filter(
      (p) => p.name.toLowerCase().includes(q) || p.brand?.toLowerCase().includes(q)
    );
  }, [otherProducts, mergeSearch]);

  const addStoreMutation = useMutation({
    mutationFn: (url: string) =>
      api.watches.create({ url, product_id: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["product-watches", id] });
      queryClient.invalidateQueries({ queryKey: ["product", id] });
      setShowAddStore(false);
      setAddUrl("");
      setAddError("");
    },
    onError: (e: Error) => setAddError(e.message),
  });

  const mergeMutation = useMutation({
    mutationFn: (sourceId: string) => api.products.merge(id, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product", id] });
      queryClient.invalidateQueries({ queryKey: ["product-watches", id] });
      setShowMerge(false);
      setMergeTarget(null);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Produkt ikke fundet</p>
        <Link href="/products" className="text-sm text-primary hover:underline">
          Tilbage til produkter
        </Link>
      </div>
    );
  }

  const suggestedDuplicates = otherProducts.filter((p) => p.score >= 0.45);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="flex items-center gap-0.5 mt-1 shrink-0">
          <Link
            href="/products"
            className="rounded-md p-1 hover:bg-muted transition-colors"
            title="Tilbage til produkter"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          {prevId && (
            <Link
              href={`/products/${prevId}`}
              className="rounded-md p-1 hover:bg-muted transition-colors"
              title="Forrige produkt"
            >
              <ChevronLeft className="h-4 w-4" />
            </Link>
          )}
          {nextId && (
            <Link
              href={`/products/${nextId}`}
              className="rounded-md p-1 hover:bg-muted transition-colors"
              title="Næste produkt"
            >
              <ChevronRight className="h-4 w-4" />
            </Link>
          )}
        </div>
        <div className="flex items-start gap-4 flex-1 min-w-0">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="h-20 w-20 rounded-lg border border-border object-contain bg-muted/20 p-1 shrink-0"
            />
          ) : (
            <div className="h-20 w-20 rounded-lg border border-border bg-muted/20 flex items-center justify-center shrink-0">
              <Package2 className="h-8 w-8 text-muted-foreground/40" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            {product.brand && (
              <p className="text-sm text-muted-foreground">{product.brand}</p>
            )}
            <h1 className="text-xl font-bold">{product.name}</h1>
            {product.ean && (
              <p className="text-xs text-muted-foreground mt-1">EAN: {product.ean}</p>
            )}
          </div>
          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => { setShowAddStore(true); setShowMerge(false); }}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              Tilføj butik
            </button>
            <button
              onClick={() => { setShowMerge(true); setShowAddStore(false); }}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              <Merge className="h-3.5 w-3.5" />
              Sammenflet
            </button>
          </div>
        </div>
      </div>

      {/* Duplicate suggestion banner */}
      {!showMerge && suggestedDuplicates.length > 0 && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 flex items-center justify-between gap-3">
          <p className="text-sm text-amber-700 dark:text-amber-400">
            <span className="font-semibold">Mulig dublet:</span>{" "}
            {suggestedDuplicates.slice(0, 2).map((p) => p.name).join(", ")} ligner dette produkt.
          </p>
          <button
            onClick={() => setShowMerge(true)}
            className="shrink-0 text-xs font-semibold text-amber-700 dark:text-amber-400 hover:underline"
          >
            Sammenflet →
          </button>
        </div>
      )}

      {/* Add store form */}
      {showAddStore && (
        <div className="rounded-lg border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Tilføj butik til dette produkt</h2>
            <button onClick={() => { setShowAddStore(false); setAddUrl(""); setAddError(""); }}>
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
          </div>
          <p className="text-sm text-muted-foreground">
            Indsæt URL til produktsiden hos en anden butik. Den overvåges automatisk under dette produkt.
          </p>
          <div className="flex gap-2">
            <input
              type="url"
              value={addUrl}
              onChange={(e) => setAddUrl(e.target.value)}
              placeholder="https://butik.dk/produkt/..."
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              disabled={!addUrl.startsWith("http") || addStoreMutation.isPending}
              onClick={() => addStoreMutation.mutate(addUrl)}
              className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm disabled:opacity-50"
            >
              {addStoreMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Tilføj
            </button>
          </div>
          {addError && <p className="text-xs text-destructive">{addError}</p>}
        </div>
      )}

      {/* Merge dialog */}
      {showMerge && (
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Sammenflet med et andet produkt</h2>
            <button onClick={() => { setShowMerge(false); setMergeTarget(null); setMergeSearch(""); }}>
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
          </div>
          <p className="text-sm text-muted-foreground">
            Alle butikker fra det valgte produkt flyttes hertil, og det tomme produkt slettes.
          </p>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="search"
              value={mergeSearch}
              onChange={(e) => setMergeSearch(e.target.value)}
              placeholder="Søg på produktnavn…"
              className="w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Product list */}
          <div className="max-h-64 overflow-y-auto divide-y divide-border rounded-md border border-border">
            {filteredProducts.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-muted-foreground">Ingen produkter fundet</p>
            )}
            {filteredProducts.map((p) => (
              <button
                key={p.id}
                onClick={() => setMergeTarget(mergeTarget?.id === p.id ? null : p)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50 ${mergeTarget?.id === p.id ? "bg-primary/10 ring-1 ring-inset ring-primary/40" : ""}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{p.name}</span>
                    {p.score >= 0.45 && (
                      <span className="shrink-0 rounded-full bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        Mulig dublet
                      </span>
                    )}
                  </div>
                  {p.lowest_price != null && (
                    <span className="text-xs text-muted-foreground">Fra {formatPrice(p.lowest_price)}</span>
                  )}
                </div>
                <div className={`h-4 w-4 rounded-full border-2 shrink-0 ${mergeTarget?.id === p.id ? "border-primary bg-primary" : "border-muted-foreground/40"}`} />
              </button>
            ))}
          </div>

          {/* Confirm */}
          {mergeTarget && (
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-4 py-3">
              <p className="text-sm">
                Flyt butikker fra <span className="font-semibold">{mergeTarget.name}</span> hertil?
              </p>
              <button
                disabled={mergeMutation.isPending}
                onClick={() => mergeMutation.mutate(mergeTarget.id)}
                className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-4 py-1.5 text-sm disabled:opacity-50"
              >
                {mergeMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Sammenflet
              </button>
            </div>
          )}
          {mergeMutation.isError && (
            <p className="text-xs text-destructive">{(mergeMutation.error as Error).message}</p>
          )}
        </div>
      )}

      {/* Combined price chart */}
      {watches.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-base font-semibold mb-4">Prishistorik</h2>
          <MultiPriceChart watches={watches} />
        </div>
      )}

      {/* Store comparison */}
      <div>
        <h2 className="text-base font-semibold mb-3">Prissammenligning</h2>
        <StoreComparison productId={id} watches={watches} />
      </div>
    </div>
  );
}
