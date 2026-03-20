import {
  DashboardStats,
  PriceEvent,
  PriceHistoryPoint,
  Product,
  ProductList,
  Shop,
  Watch,
  WatchCreate,
  WatchDetectResult,
  WatchList,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}/api/v1${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const api = {
  dashboard: {
    stats: () => apiFetch<DashboardStats>("/dashboard/stats"),
    recentEvents: (limit = 20) =>
      apiFetch<PriceEvent[]>(`/dashboard/recent-events?limit=${limit}`),
  },

  // ─── Watches ────────────────────────────────────────────────────────────────
  watches: {
    list: (params?: {
      skip?: number;
      limit?: number;
      status?: string;
      shop_id?: string;
      product_id?: string;
      search?: string;
    }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      if (params?.status) qs.set("status", params.status);
      if (params?.shop_id) qs.set("shop_id", params.shop_id);
      if (params?.product_id) qs.set("product_id", params.product_id);
      if (params?.search) qs.set("search", params.search);
      return apiFetch<WatchList>(`/watches?${qs}`);
    },
    get: (id: string) => apiFetch<Watch>(`/watches/${id}`),
    create: (data: WatchCreate) =>
      apiFetch<Watch>("/watches", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<WatchCreate & { is_active: boolean; status: string }>) =>
      apiFetch<Watch>(`/watches/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<void>(`/watches/${id}`, { method: "DELETE" }),
    triggerCheck: (id: string) =>
      apiFetch<Watch>(`/watches/${id}/check`, { method: "POST" }),
    detect: (url: string) =>
      apiFetch<WatchDetectResult>("/watches/detect", {
        method: "POST",
        body: JSON.stringify({ url }),
      }),
  },

  // ─── History ────────────────────────────────────────────────────────────────
  history: {
    prices: (watchId: string, params?: { limit?: number; since?: string }) => {
      const qs = new URLSearchParams();
      if (params?.limit) qs.set("limit", String(params.limit));
      if (params?.since) qs.set("since", params.since);
      return apiFetch<PriceHistoryPoint[]>(
        `/history/watches/${watchId}/prices?${qs}`
      );
    },
    events: (watchId: string, limit = 50) =>
      apiFetch<PriceEvent[]>(
        `/history/watches/${watchId}/events?limit=${limit}`
      ),
  },

  // ─── Products ────────────────────────────────────────────────────────────────
  products: {
    list: (params?: { skip?: number; limit?: number; search?: string }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      if (params?.search) qs.set("search", params.search);
      return apiFetch<ProductList>(`/products?${qs}`);
    },
    get: (id: string) => apiFetch<Product>(`/products/${id}`),
  },

  // ─── Shops ───────────────────────────────────────────────────────────────────
  shops: {
    list: () => apiFetch<Shop[]>("/shops"),
    update: (id: string, data: Partial<Pick<Shop, "is_active">>) =>
      apiFetch<Shop>(`/shops/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },
};
