from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ShopRead(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    logo_url: str | None = None
    default_provider: str
    is_active: bool
    watch_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopUpdate(BaseModel):
    default_provider: str | None = None
    default_price_selector: str | None = None
    default_title_selector: str | None = None
    default_stock_selector: str | None = None
    is_active: bool | None = None


class PriceHistoryPoint(BaseModel):
    recorded_at: datetime
    price: float | None = None
    stock_status: str | None = None
    is_change: bool

    model_config = {"from_attributes": True}


class PriceEventRead(BaseModel):
    id: uuid.UUID
    watch_id: uuid.UUID
    event_type: str
    old_price: float | None = None
    new_price: float | None = None
    price_delta: float | None = None
    price_delta_pct: float | None = None
    old_stock: str | None = None
    new_stock: str | None = None
    occurred_at: datetime
    extra_data: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_watches: int
    active_watches: int
    error_watches: int
    blocked_watches: int
    price_drops_today: int
    price_increases_today: int
    checks_today: int
    total_products: int
