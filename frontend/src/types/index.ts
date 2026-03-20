// ─── Shops ────────────────────────────────────────────────────────────────────
export interface Shop {
  id: string;
  name: string;
  domain: string;
  logo_url: string | null;
  default_provider: string;
  is_active: boolean;
  watch_count: number;
  created_at: string;
  updated_at: string;
}

// ─── Products ─────────────────────────────────────────────────────────────────
export interface Product {
  id: string;
  name: string;
  brand: string | null;
  description: string | null;
  image_url: string | null;
  ean: string | null;
  is_active: boolean;
  watch_count: number;
  lowest_price: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProductList {
  items: Product[];
  total: number;
}

// ─── Watches ──────────────────────────────────────────────────────────────────
export type WatchStatus = "pending" | "active" | "paused" | "error" | "blocked";

export interface WatchShopSummary {
  id: string;
  name: string;
  domain: string;
  logo_url: string | null;
}

export interface Watch {
  id: string;
  url: string;
  title: string | null;
  image_url: string | null;
  current_price: number | null;
  current_currency: string;
  current_stock_status: string | null;
  status: WatchStatus;
  last_checked_at: string | null;
  last_changed_at: string | null;
  last_error: string | null;
  error_count: number;
  check_interval: number;
  provider: string;
  scraper_config: Record<string, string> | null;
  is_active: boolean;
  shop: WatchShopSummary | null;
  product_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface WatchList {
  items: Watch[];
  total: number;
}

export interface WatchCreate {
  url: string;
  product_id?: string | null;
  check_interval?: number;
  provider?: string;
  scraper_config?: Record<string, string> | null;
}

export interface WatchDetectResult {
  url: string;
  detected_title: string | null;
  detected_price: number | null;
  detected_currency: string | null;
  detected_stock: string | null;
  detected_image_url: string | null;
  suggested_provider: string;
  suggested_price_selector: string | null;
  confidence: "low" | "medium" | "high";
  shop_domain: string | null;
  error: string | null;
}

// ─── History ──────────────────────────────────────────────────────────────────
export interface PriceHistoryPoint {
  recorded_at: string;
  price: number | null;
  stock_status: string | null;
  is_change: boolean;
}

export interface PriceEvent {
  id: string;
  watch_id: string;
  event_type: string;
  old_price: number | null;
  new_price: number | null;
  price_delta: number | null;
  price_delta_pct: number | null;
  old_stock: string | null;
  new_stock: string | null;
  occurred_at: string;
  metadata: Record<string, unknown> | null;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export interface DashboardStats {
  total_watches: number;
  active_watches: number;
  error_watches: number;
  blocked_watches: number;
  price_drops_today: number;
  price_increases_today: number;
  checks_today: number;
  total_products: number;
}
