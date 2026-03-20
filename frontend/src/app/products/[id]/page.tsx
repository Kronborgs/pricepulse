"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Package2 } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { StoreComparison } from "@/components/products/store-comparison";

export default function ProductDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.products.get(id),
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
        <Link
          href="/products"
          className="text-sm text-primary hover:underline"
        >
          Tilbage til produkter
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          href="/products"
          className="mt-1 rounded-md p-1 hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-start gap-4 flex-1">
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
          <div className="min-w-0">
            {product.brand && (
              <p className="text-sm text-muted-foreground">{product.brand}</p>
            )}
            <h1 className="text-xl font-bold">{product.name}</h1>
            {product.ean && (
              <p className="text-xs text-muted-foreground mt-1">
                EAN: {product.ean}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Store comparison */}
      <div>
        <h2 className="text-base font-semibold mb-3">Prissammenligning</h2>
        <StoreComparison productId={id} />
      </div>
    </div>
  );
}
