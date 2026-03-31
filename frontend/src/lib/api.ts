import {
  AIJob,
  AIJobDetail,
  AIJobList,
  DashboardStats,
  EmailPreferences,
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
  SetupStatus,
  Shop,
  SMTPStatus,
  SourceCheck,
  SourceCheckList,
  SourcePriceEvent,
  TimelineEvent,
  User,
  UserList,
  Watch,
  WatchCreate,
  WatchDetectResult,
  WatchList,
  WatchSource,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

let _refreshing: Promise<boolean> | null = null;

async function _silentRefresh(): Promise<boolean> {
  // Deduplicate — kun ét refresh-kald ad gangen
  if (_refreshing) return _refreshing;
  _refreshing = fetch(`${BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => { _refreshing = null; });
  return _refreshing;
}

async function apiFetch<T>(path: string, init?: RequestInit, _retried = false): Promise<T> {
  const url = `${BASE_URL}/api/v1${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "include",
    ...init,
  });

  // Forsøg stille token-refresh ved 401 (undtagen på selve auth-endpoints)
  if (
    res.status === 401 &&
    !_retried &&
    path !== "/auth/refresh" &&
    path !== "/auth/login" &&
    path !== "/auth/setup" &&
    path !== "/auth/setup-restore"
  ) {
    const refreshed = await _silentRefresh();
    if (refreshed) {
      return apiFetch<T>(path, init, true);
    }
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
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
      owner_ids?: string[];
    }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      if (params?.status) qs.set("status", params.status);
      if (params?.shop_id) qs.set("shop_id", params.shop_id);
      if (params?.product_id) qs.set("product_id", params.product_id);
      if (params?.search) qs.set("search", params.search);
      params?.owner_ids?.forEach((id) => qs.append("owner_ids", id));
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
    list: (params?: { skip?: number; limit?: number; search?: string; owner_ids?: string[] }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      if (params?.search) qs.set("search", params.search);
      params?.owner_ids?.forEach((id) => qs.append("owner_ids", id));
      return apiFetch<ProductList>(`/products?${qs}`);
    },
    get: (id: string) => apiFetch<Product>(`/products/${id}`),
    merge: (targetId: string, sourceProductId: string) =>
      apiFetch<Product>(`/products/${targetId}/merge`, {
        method: "POST",
        body: JSON.stringify({ source_product_id: sourceProductId }),
      }),
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

  // ─── Auth ─────────────────────────────────────────────────────────────────
  auth: {
    setupStatus: () => apiFetch<SetupStatus>("/auth/setup-status"),
    setup: (data: { email: string; password: string; display_name?: string }) =>
      apiFetch<User>("/auth/setup", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    setupRestore: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiFetch<{ ok: boolean; stats: Record<string, number> }>("/auth/setup-restore", {
        method: "POST",
        body: fd,
        headers: {},
      });
    },
    login: (data: { email: string; password: string }) =>
      apiFetch<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    logout: () => apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" }),
    me: () => apiFetch<User>("/auth/me"),
    forgotPassword: (email: string) =>
      apiFetch<{ ok: boolean }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, new_password: string) =>
      apiFetch<{ ok: boolean }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password }),
      }),
  },

  // ─── Admin: Brugere ───────────────────────────────────────────────────────
  adminUsers: {
    list: (params?: { skip?: number; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      return apiFetch<UserList>(`/auth/admin/users?${qs}`);
    },
    create: (data: { email: string; password?: string; role?: string; display_name?: string }) =>
      apiFetch<User>("/auth/admin/users", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { display_name?: string; role?: string; is_active?: boolean; session_timeout_minutes?: number }) =>
      apiFetch<User>(`/auth/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      fetch(`${BASE_URL}/api/v1/auth/admin/users/${id}`, {
        method: "DELETE",
        credentials: "include",
      }).then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
      }),
  },

  // ─── AI Jobs ──────────────────────────────────────────────────────────────
  aiJobs: {
    list: (params?: {
      job_type?: string;
      status?: string;
      source_id?: string;
      watch_id?: string;
      skip?: number;
      limit?: number;
    }) => {
      const qs = new URLSearchParams();
      if (params?.job_type) qs.set("job_type", params.job_type);
      if (params?.status) qs.set("status", params.status);
      if (params?.source_id) qs.set("source_id", params.source_id);
      if (params?.watch_id) qs.set("watch_id", params.watch_id);
      if (params?.skip != null) qs.set("skip", String(params.skip));
      if (params?.limit != null) qs.set("limit", String(params.limit));
      return apiFetch<AIJobList>(`/ai/jobs?${qs}`);
    },
    get: (id: string) => apiFetch<AIJobDetail>(`/ai/jobs/${id}`),
    cancel: (id: string) =>
      apiFetch<{ ok: boolean }>(`/ai/jobs/${id}/cancel`, { method: "POST" }),
    diagnoseSource: (sourceId: string) =>
      apiFetch<{ ok: boolean; message: string }>(`/ai/diagnose/source/${sourceId}`, {
        method: "POST",
      }),
    stats: () => apiFetch<{ by_type_status: unknown[] }>("/ai/stats"),
  },

  // ─── SMTP / Email ────────────────────────────────────────────────────────
  smtp: {
    get: () => apiFetch<SMTPStatus>("/admin/smtp"),
    save: (data: {
      host: string;
      port: number;
      use_tls: boolean;
      username: string;
      password: string;
      from_email: string;
      from_name: string;
    }) =>
      apiFetch<{ ok: boolean }>("/admin/smtp", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    test: (to_email: string) =>
      apiFetch<{ ok: boolean }>("/admin/smtp/test", {
        method: "POST",
        body: JSON.stringify({ to_email }),
      }),
  },

  emailPreferences: {
    get: () => apiFetch<EmailPreferences>("/me/email-preferences"),
    update: (data: Partial<EmailPreferences>) =>
      apiFetch<{ ok: boolean }>("/me/email-preferences", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  // ─── Admin: Data management ───────────────────────────────────────────────
  adminData: {
    stats: () => apiFetch<{
      watches_v1: number;
      watches_v2: number;
      products: number;
      price_history_v1: number;
      price_events_v2: number;
      ai_jobs: number;
      email_queue: number;
      source_checks: number;
      users: number;
    }>("/admin/data/stats"),
    deleteWatches: () =>
      apiFetch<{ ok: boolean }>("/admin/data/watches", { method: "DELETE" }),
    deleteProducts: () =>
      apiFetch<{ ok: boolean }>("/admin/data/products", { method: "DELETE" }),
    deletePriceHistory: () =>
      apiFetch<{ ok: boolean }>("/admin/data/price-history", { method: "DELETE" }),
    deleteAiJobs: () =>
      apiFetch<{ ok: boolean }>("/admin/data/ai-jobs", { method: "DELETE" }),
    deleteEmailQueue: () =>
      apiFetch<{ ok: boolean }>("/admin/data/email-queue", { method: "DELETE" }),
  },

  // ─── Admin: Backup ────────────────────────────────────────────────────────
  backup: {
    list: () => apiFetch<{ filename: string; size_bytes: number; created_at: string }[]>("/admin/backup/list"),
    run: () => apiFetch<{ ok: boolean; filename: string }>("/admin/backup/run", { method: "POST" }),
    getConfig: () => apiFetch<{ enabled: boolean; interval_hours: number; keep_count: number }>("/admin/backup/config"),
    updateConfig: (data: { enabled: boolean; interval_hours: number; keep_count: number }) =>
      apiFetch<{ enabled: boolean; interval_hours: number; keep_count: number }>("/admin/backup/config", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    restore: (filename: string, importUsers: boolean) =>
      apiFetch<{ ok: boolean; stats: Record<string, number> }>(`/admin/backup/restore/${encodeURIComponent(filename)}`, {
        method: "POST",
        body: JSON.stringify({ import_users: importUsers }),
      }),
    uploadRestore: (file: File, importUsers: boolean) => {
      const form = new FormData();
      form.append("file", file);
      return apiFetch<{ ok: boolean; stats: Record<string, number> }>(
        `/admin/backup/upload-restore?import_users=${importUsers}`,
        { method: "POST", body: form, headers: {} },
      );
    },
    deleteBackup: (filename: string) =>
      apiFetch<{ ok: boolean }>(`/admin/backup/${encodeURIComponent(filename)}`, { method: "DELETE" }),
    downloadUrl: (filename: string) => `/api/v1/admin/backup/download/${encodeURIComponent(filename)}`,
  },
};
