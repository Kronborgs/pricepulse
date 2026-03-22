from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    brand: str | None = None
    description: str | None = None
    image_url: str | None = None
    ean: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    description: str | None = None
    image_url: str | None = None
    ean: str | None = None
    is_active: bool | None = None


class ProductRead(BaseModel):
    id: uuid.UUID
    name: str
    brand: str | None = None
    description: str | None = None
    image_url: str | None = None
    ean: str | None = None
    is_active: bool
    watch_count: int = 0
    lowest_price: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int = 0


class MergeProductRequest(BaseModel):
    source_product_id: uuid.UUID
    total: int
