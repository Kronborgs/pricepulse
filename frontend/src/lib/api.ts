import {
  DashboardStats,
  LlmParserAdvice,
  NormalizedProduct,
  OllamaStatus,
  PriceEvent,
  PriceHistoryPoint,
  Product,
  ProductList,
  ProductWatch,
  ProductWatchCreate,
  ProductWatchList,
  Shop,
  SourceCheck,
  SourceCheckList,
  SourcePriceEvent,
  TimelineEvent,
  Watch,
  WatchCreate,
  WatchDetectResult,
  WatchList,
  WatchSource,
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

  // ─── ProductWatches (v2) ─────────────────────────────────────────────────────
  productWatches: {
    list: (params?: { skip?: number; limit?: number; status?: string; search?: string }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      if (params?.status) qs.set("status", params.status);
      if (params?.search) qs.set("search", params.search);
      return apiFetch<ProductWatchList>(`/product-watches?${qs}`);
    },
    get: (id: string) => apiFetch<ProductWatch>(`/product-watches/${id}`),
    create: (data: ProductWatchCreate) =>
      apiFetch<ProductWatch>("/product-watches", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { name?: string | null; default_interval_min?: number }) =>
      apiFetch<ProductWatch>(`/product-watches/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    pause: (id: string) =>
      apiFetch<ProductWatch>(`/product-watches/${id}/pause`, { method: "POST" }),
    resume: (id: string) =>
      apiFetch<ProductWatch>(`/product-watches/${id}/resume`, { method: "POST" }),
    timeline: (id: string, limit = 50) =>
      apiFetch<TimelineEvent[]>(`/product-watches/${id}/timeline?limit=${limit}`),
    addSource: (id: string, data: { url: string; provider?: string; interval_override_min?: number; scraper_config?: Record<string, string> }) =>
      apiFetch<WatchSource>(`/product-watches/${id}/sources`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // ─── Sources (v2) ────────────────────────────────────────────────────────────
  sources: {
    get: (id: string) => apiFetch<WatchSource>(`/sources/${id}`),
    update: (id: string, data: { url?: string; interval_override_min?: number | null; provider?: string; scraper_config?: Record<string, string> | null }) =>
      apiFetch<WatchSource>(`/sources/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    archive: (id: string) =>
      apiFetch<void>(`/sources/${id}`, { method: "DELETE" }),
    pause: (id: string) =>
      apiFetch<WatchSource>(`/sources/${id}/pause`, { method: "POST" }),
    resume: (id: string) =>
      apiFetch<WatchSource>(`/sources/${id}/resume`, { method: "POST" }),
    check: (id: string) =>
      apiFetch<WatchSource>(`/sources/${id}/check`, { method: "POST" }),
    checks: (id: string, params?: { skip?: number; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      return apiFetch<SourceCheckList>(`/sources/${id}/checks?${qs}`);
    },
    priceEvents: (id: string, limit = 50) =>
      apiFetch<SourcePriceEvent[]>(`/sources/${id}/price-events?limit=${limit}`),
    diagnose: (id: string) =>
      apiFetch<{ status: string }>(`/sources/${id}/diagnose`, { method: "POST" }),
  },

  // ─── Ollama (v2) ─────────────────────────────────────────────────────────────
  ollama: {
    status: () => apiFetch<OllamaStatus>("/ollama/status"),
    updateConfig: (data: {
      enabled?: boolean;
      host?: string;
      parser_model?: string;
      normalize_model?: string;
      embed_model?: string;
    }) =>
      apiFetch<OllamaStatus>("/ollama/config", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    analyzeParser: (data: { html: string; url: string; existing_config?: Record<string, string> | null }) =>
      apiFetch<LlmParserAdvice>("/ollama/analyze-parser", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    normalizeProduct: (titles: string[]) =>
      apiFetch<NormalizedProduct>("/ollama/normalize-product", {
        method: "POST",
        body: JSON.stringify({ titles }),
      }),
  },
};
