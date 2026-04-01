from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


# ─── Watch schemas ────────────────────────────────────────────────────────────

class WatchCreate(BaseModel):
    url: str
    product_id: uuid.UUID | None = None
    check_interval: int = 360
    provider: str = "curl_cffi"
    scraper_config: dict[str, Any] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL skal starte med http:// eller https://")
        return v.strip()

    @field_validator("check_interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("check_interval skal være mindst 5 minutter")
        if v > 10080:  # 1 uge
            raise ValueError("check_interval må max være 10080 minutter (1 uge)")
        return v


class WatchUpdate(BaseModel):
    title: str | None = None
    product_id: uuid.UUID | None = None
    check_interval: int | None = None
    provider: str | None = None
    scraper_config: dict[str, Any] | None = None
    is_active: bool | None = None
    status: str | None = None


class WatchShopSummary(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class WatchRead(BaseModel):
    id: uuid.UUID
    url: str
    title: str | None = None
    image_url: str | None = None
    current_price: float | None = None
    current_currency: str = "DKK"
    current_stock_status: str | None = None
    status: str
    last_checked_at: datetime | None = None
    last_changed_at: datetime | None = None
    last_error: str | None = None
    error_count: int
    check_interval: int
    provider: str
    scraper_config: dict[str, Any] | None = None
    last_diagnostic: dict[str, Any] | None = None
    is_active: bool
    shop: WatchShopSummary | None = None
    product_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WatchList(BaseModel):
    items: list[WatchRead]
    total: int


class WatchDetectResult(BaseModel):
    """Returneres ved auto-detect af pris/titel fra URL."""
    url: str
    detected_title: str | None = None
    detected_price: float | None = None
    detected_currency: str | None = None
    detected_stock: str | None = None
    detected_image_url: str | None = None
    suggested_provider: str = "http"
    suggested_price_selector: str | None = None
    confidence: str = "low"  # low | medium | high
    shop_domain: str | None = None
    error: str | None = None
