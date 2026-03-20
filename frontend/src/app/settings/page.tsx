"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Shop } from "@/types";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Indstillinger</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Konfigurer butikker og systemindstillinger
        </p>
      </div>

      <HealthCard />
      <ShopsSection />
    </div>
  );
}

function HealthCard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("unhealthy");
      return res.json() as Promise<{ status: string; environment: string }>;
    },
    retry: false,
  });

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-base font-semibold mb-4">Systemstatus</h2>
      <div className="flex items-center gap-2">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : error ? (
          <>
            <XCircle className="h-4 w-4 text-destructive" />
            <span className="text-sm text-destructive">Backend ikke nåbar</span>
          </>
        ) : (
          <>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span className="text-sm">
              Backend kører{" "}
              <span className="text-muted-foreground">
                ({data?.environment ?? "—"})
              </span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function ShopsSection() {
  const queryClient = useQueryClient();

  const { data: shops, isLoading } = useQuery({
    queryKey: ["shops"],
    queryFn: api.shops.list,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.shops.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shops"] }),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-base font-semibold mb-4">Butikker</h2>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const shopList: Shop[] = shops ?? [];

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-semibold">Butikker</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Aktiver eller deaktiver butikker der scrapes
        </p>
      </div>
      <div className="divide-y divide-border">
        {shopList.map((shop) => (
          <ShopRow
            key={shop.id}
            shop={shop}
            onToggle={(is_active) =>
              toggleMutation.mutate({ id: shop.id, is_active })
            }
            isPending={toggleMutation.isPending}
          />
        ))}
        {shopList.length === 0 && (
          <p className="px-5 py-6 text-sm text-muted-foreground">
            Ingen butikker. Kør seed-scriptet for at tilføje dem.
          </p>
        )}
      </div>
    </div>
  );
}

function ShopRow({
  shop,
  onToggle,
  isPending,
}: {
  shop: Shop;
  onToggle: (is_active: boolean) => void;
  isPending: boolean;
}) {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="flex-1 min-w-0">
        <p className="font-medium">{shop.name}</p>
        <p className="text-xs text-muted-foreground">
          {shop.domain} · {shop.default_provider} ·{" "}
          {shop.watch_count} watch{shop.watch_count !== 1 ? "es" : ""}
        </p>
      </div>

      <button
        onClick={() => onToggle(!shop.is_active)}
        disabled={isPending}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 ${
          shop.is_active ? "bg-primary" : "bg-muted"
        }`}
        aria-label={shop.is_active ? "Deaktiver butik" : "Aktiver butik"}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
            shop.is_active ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
