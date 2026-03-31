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
  owner_id: string | null;
  owner_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductList {
  items: Product[];
  total: number;
}

// ─── Watches ──────────────────────────────────────────────────────────────────
export type WatchStatus = "pending" | "active" | "paused" | "error" | "blocked" | "ai_analyzing" | "ai_active";

export type ScrapeErrorType =
  | "parser_mismatch"
  | "js_render_required"
  | "bot_protection"
  | "transport_error"
  | "timeout"
  | "comparison_site"
  | "http_error";

export const ERROR_TYPE_LABELS: Record<ScrapeErrorType, { short: string; action: string }> = {
  parser_mismatch:    { short: "Parser fandt ingen pris",            action: "Konfigurér CSS-selectors manuelt" },
  js_render_required: { short: "Siden kræver JavaScript-rendering",  action: "Aktivér Playwright-provider" },
  bot_protection:     { short: "Bot-beskyttelse aktiv",              action: "Siden blokerer scraping" },
  transport_error:    { short: "Netværksfejl",                       action: "Genprøver automatisk" },
  timeout:            { short: "Timeout",                            action: "Siden svarer for langsomt" },
  comparison_site:    { short: "Prissammenligningsside",             action: "Tilføj en direkte butiksside" },
  http_error:         { short: "HTTP-fejl",                          action: "Tjek om URL er tilgængelig" },
};

export interface WatchDiagnostic {
  checked_at: string;
  fetch: {
    status_code: number;
    provider: string;
    response_time_ms: number;
    html_length: number;
    final_url: string | null;
  };
  parse: {
    extractors_tried: string[];
    parser_used: string | null;
    price_found: number | null;
  };
  error_type: ScrapeErrorType | null;
  recommended_action: string | null;
  ollama_advice?: {
    reasoning: string;
    recommended_action: string;
    price_selector: string | null;
    stock_selector: string | null;
    requires_js: boolean;
    likely_bot_protection: boolean;
    confidence: number;
    page_type: string;
  } | null;
}

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
  last_diagnostic: WatchDiagnostic | null;
  is_active: boolean;
  shop: WatchShopSummary | null;
  product_id: string | null;
  owner_id: string | null;
  owner_name: string | null;
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
  extra_data: Record<string, unknown> | null;
  watch_title: string | null;
  watch_image_url: string | null;
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

// ─── v2: WatchSource ──────────────────────────────────────────────────────────
export type SourceStatus = "pending" | "active" | "paused" | "error" | "blocked" | "archived" | "ai_analyzing" | "ai_active";

export interface WatchSource {
  id: string;
  watch_id: string;
  shop: string;
  url: string;
  previous_url: string | null;
  status: SourceStatus;
  interval_override_min: number | null;
  last_check_at: string | null;
  next_check_at: string | null;
  last_price: number | null;
  last_currency: string;
  last_stock_status: string | null;
  last_error_type: ScrapeErrorType | null;
  last_error_message: string | null;
  last_diagnostic: WatchDiagnostic | null;
  consecutive_errors: number;
  bot_suspected_at: string | null;
  provider: string;
  scraper_config: Record<string, string> | null;
  paused_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

// ─── v2: ProductWatch ────────────────────────────────────────────────────────
export type ProductWatchStatus = "pending" | "active" | "partial" | "paused" | "error" | "archived";

export interface ProductWatch {
  id: string;
  product_id: string;
  name: string | null;
  default_interval_min: number;
  status: ProductWatchStatus;
  last_best_price: number | null;
  last_best_source_id: string | null;
  last_checked_at: string | null;
  paused_at: string | null;
  archived_at: string | null;
  sources: WatchSource[];
  created_at: string;
  updated_at: string;
}

export interface ProductWatchList {
  items: ProductWatch[];
  total: number;
}

export interface ProductWatchCreate {
  url: string;
  name?: string | null;
  product_id?: string | null;
  default_interval_min?: number;
  provider?: string;
  scraper_config?: Record<string, string> | null;
}

// ─── v2: SourceCheck ─────────────────────────────────────────────────────────
export interface SourceCheck {
  id: number;
  source_id: string;
  checked_at: string;
  price: number | null;
  currency: string;
  stock_status: string | null;
  success: boolean;
  status_code: number | null;
  response_time_ms: number | null;
  html_length: number | null;
  error_type: ScrapeErrorType | null;
  error_message: string | null;
  extractor_used: string | null;
  bot_suspected: boolean;
  is_price_change: boolean;
  is_stock_change: boolean;
  raw_diagnostic: WatchDiagnostic | null;
}

export interface SourceCheckList {
  items: SourceCheck[];
  total: number;
}

// ─── v2: SourcePriceEvent ────────────────────────────────────────────────────
export type ChangeType = "initial" | "increase" | "decrease" | "unavailable" | "back_in_stock";

export interface SourcePriceEvent {
  id: number;
  source_id: string;
  old_price: number | null;
  new_price: number | null;
  old_stock: string | null;
  new_stock: string | null;
  change_type: ChangeType;
  created_at: string;
}

// ─── v2: Timeline ────────────────────────────────────────────────────────────
export interface TimelineEvent {
  id: number;
  watch_id: string;
  source_id: string | null;
  event_type: string;
  event_data: Record<string, unknown> | null;
  created_at: string;
}

// ─── v2: Grafer ──────────────────────────────────────────────────────────────
export interface GraphPoint {
  ts: string;
  value: number | null;
}

export interface SourceGraph {
  prices: GraphPoint[];
  stock_statuses: Array<{ ts: string; stock_status: string | null }>;
}

export interface ProductGraph {
  best_price: GraphPoint[];
  avg_price: GraphPoint[];
  min_price: GraphPoint[];
}

// ─── v2: Ollama ──────────────────────────────────────────────────────────────
export interface OllamaStatus {
  available: boolean;
  enabled: boolean;
  models: string[];
  host: string;
  parser_model: string;
  normalize_model: string;
  embed_model: string;
}

export interface LlmParserAdvice {
  page_type: "product" | "listing" | "blocked" | "captcha" | "unknown";
  price_selector: string | null;
  stock_selector: string | null;
  requires_js: boolean;
  likely_bot_protection: boolean;
  reasoning: string;
  recommended_action: string;
  confidence: number;
}

export interface NormalizedProduct {
  brand: string | null;
  model: string | null;
  variant: string | null;
  mpn: string | null;
  normalized_key: string | null;
  confidence: number;
  reasoning: string;
}

// ─── Auth / Users ─────────────────────────────────────────────────────────────
export type UserRole = "admin" | "superuser" | "user";

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  role: UserRole;
  is_active: boolean;
  email_verified: boolean;
  session_timeout_minutes: number | null;
  created_at: string;
}

export interface UserList {
  items: User[];
  total: number;
}

export interface SetupStatus {
  setup_required: boolean;
}

// ─── AI Jobs ──────────────────────────────────────────────────────────────────
export type AIJobType = "parser_advice" | "normalization" | "product_matching" | "selector_suggest";
export type AIJobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";

export interface AIJob {
  id: string;
  job_type: AIJobType;
  status: AIJobStatus;
  model_used: string | null;
  source_id: string | null;
  watch_id: string | null;
  product_id: string | null;
  triggered_by: string | null;
  prompt_summary: string | null;
  summary: string | null;
  error_message: string | null;
  prompt_tokens: number | null;
  response_tokens: number | null;
  duration_ms: number | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AIJobDetail extends AIJob {
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
}

export interface AIJobList {
  items: AIJob[];
  total: number;
}

// ─── Email Preferences ────────────────────────────────────────────────────────
export interface EmailPreferences {
  notify_price_drop: boolean;
  notify_back_in_stock: boolean;
  notify_new_error: boolean;
  notify_on_change: boolean;
  digest_enabled: boolean;
  digest_frequency: "hourly" | "daily" | "weekly" | "monthly";
  digest_day_of_week: number;
}

// ─── SMTP Settings ────────────────────────────────────────────────────────────
export interface SMTPSettings {
  id: number;
  is_active: boolean;
  host: string;
  port: number;
  use_tls: boolean;
  username: string;
  from_email: string;
  from_name: string;
}

export interface SMTPStatus {
  configured: boolean;
  settings?: SMTPSettings;
}

// ─── Scraper Reports ──────────────────────────────────────────────────────────
export type ReportStatus = "new" | "read" | "resolved";

export interface ScraperReport {
  id: string;
  watch_id: string;
  comment: string | null;
  status: ReportStatus;
  created_at: string;
  reporter: { id: string; email: string; display_name: string | null };
  watch: { id: string; url: string; title: string | null };
}

export interface ScraperReportList {
  items: ScraperReport[];
  total: number;
  unread: number;
}

