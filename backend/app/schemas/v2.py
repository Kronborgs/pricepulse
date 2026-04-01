from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


# ── WatchSource schemas ───────────────────────────────────────────────────────

class WatchSourceCreate(BaseModel):
    url: str
    interval_override_min: int | None = None
    provider: str = "curl_cffi"
    scraper_config: dict[str, Any] | None = None
    currency_hint: str | None = None  # Manuelt sat valuta (f.eks. SEK, NOK) — bruges når parser ikke kan detektere

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL skal starte med http:// eller https://")
        return v.strip()

    @field_validator("currency_hint")
    @classmethod
    def validate_currency_hint(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().upper()
            if len(v) != 3:
                raise ValueError("Valutakode skal være 3 bogstaver (ISO 4217)")
        return v or None


class WatchSourceUpdate(BaseModel):
    url: str | None = None
    interval_override_min: int | None = None
    provider: str | None = None
    scraper_config: dict[str, Any] | None = None
    currency_hint: str | None = None


class WatchSourceRead(BaseModel):
    id: uuid.UUID
    watch_id: uuid.UUID
    shop: str
    url: str
    previous_url: str | None = None
    status: str
    interval_override_min: int | None = None
    last_check_at: datetime | None = None
    next_check_at: datetime | None = None
    last_price: float | None = None          # DKK (konverteret)
    last_price_raw: float | None = None      # Original pris i last_currency
    last_currency: str = "DKK"
    currency_hint: str | None = None
    last_stock_status: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    last_diagnostic: dict[str, Any] | None = None
    consecutive_errors: int
    bot_suspected_at: datetime | None = None
    provider: str
    scraper_config: dict[str, Any] | None = None
    paused_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── ProductWatch schemas ──────────────────────────────────────────────────────

class ProductWatchCreate(BaseModel):
    """Opret product watch med første source URL."""
    url: str
    name: str | None = None
    product_id: uuid.UUID | None = None
    default_interval_min: int = 60
    provider: str = "curl_cffi"
    scraper_config: dict[str, Any] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL skal starte med http:// eller https://")
        return v.strip()

    @field_validator("default_interval_min")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("default_interval_min skal være mindst 5")
        if v > 10080:
            raise ValueError("default_interval_min må max være 10080 (1 uge)")
        return v


class ProductWatchUpdate(BaseModel):
    name: str | None = None
    default_interval_min: int | None = None
    status: str | None = None


class ProductWatchRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    name: str | None = None
    default_interval_min: int
    status: str
    last_best_price: float | None = None
    last_best_source_id: uuid.UUID | None = None
    last_checked_at: datetime | None = None
    paused_at: datetime | None = None
    archived_at: datetime | None = None
    sources: list[WatchSourceRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductWatchList(BaseModel):
    items: list[ProductWatchRead]
    total: int


# ── SourceCheck schemas ───────────────────────────────────────────────────────

class SourceCheckRead(BaseModel):
    id: int
    source_id: uuid.UUID
    checked_at: datetime
    price: float | None = None
    currency: str = "DKK"
    stock_status: str | None = None
    success: bool
    status_code: int | None = None
    response_time_ms: int | None = None
    html_length: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    extractor_used: str | None = None
    bot_suspected: bool
    is_price_change: bool
    is_stock_change: bool
    raw_diagnostic: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SourceCheckList(BaseModel):
    items: list[SourceCheckRead]
    total: int


# ── SourcePriceEvent schemas ──────────────────────────────────────────────────

class SourcePriceEventRead(BaseModel):
    id: int
    source_id: uuid.UUID
    old_price: float | None = None
    new_price: float | None = None
    old_stock: str | None = None
    new_stock: str | None = None
    change_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Timeline schemas ──────────────────────────────────────────────────────────

class TimelineEventRead(BaseModel):
    id: int
    watch_id: uuid.UUID
    source_id: uuid.UUID | None = None
    event_type: str
    event_data: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Graph schemas ─────────────────────────────────────────────────────────────

class GraphPoint(BaseModel):
    ts: datetime
    value: float | None


class SourceGraph(BaseModel):
    prices: list[GraphPoint]
    stock_statuses: list[dict]  # [{ts, stock_status}]


class ProductGraph(BaseModel):
    best_price: list[GraphPoint]
    avg_price: list[GraphPoint]
    min_price: list[GraphPoint]


# ── Ollama schemas ────────────────────────────────────────────────────────────

class OllamaStatusResponse(BaseModel):
    available: bool
    enabled: bool
    models: list[str] = []
    host: str
    parser_model: str
    normalize_model: str
    embed_model: str


class OllamaConfigPatch(BaseModel):
    enabled: bool | None = None
    host: str | None = None
    parser_model: str | None = None
    normalize_model: str | None = None
    embed_model: str | None = None


class OllamaAnalyzeRequest(BaseModel):
    url: str
    html_snippet: str
    html_title: str = ""
    status_code: int = 200
    failed_extractors: list[str] = []


class OllamaNormalizeRequest(BaseModel):
    titles: list[str]
