from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.price_event import PriceEvent
    from app.models.price_history import PriceHistory
    from app.models.product import Product
    from app.models.shop import Shop
    from app.models.user import User


class Watch(Base, TimestampMixin):
    """
    Kerneentiteten. Én Watch = én URL der overvåges.
    Kan knyttes til et Product (valgfrit) og en Shop (auto-detekteret).
    """

    __tablename__ = "watches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Ejerskab
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Valgfri grupperinger
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # URL og titel
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)

    # Valutahint: bruges til konvertering når parseren ikke detekterer valuta
    currency_hint: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Seneste scrapede data
    current_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    current_price_raw: Mapped[float | None] = mapped_column(Numeric(10, 4))
    current_currency: Mapped[str] = mapped_column(String(3), default="DKK", nullable=False)
    current_stock_status: Mapped[str | None] = mapped_column(String(100))

    # Status
    # pending | active | paused | error | blocked
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scraper-konfiguration
    check_interval: Mapped[int] = mapped_column(Integer, default=360, nullable=False)  # minutter
    provider: Mapped[str] = mapped_column(String(50), default="curl_cffi", nullable=False)

    # JSONB: {price_selector, title_selector, stock_selector, wait_for_selector, ...}
    scraper_config: Mapped[dict | None] = mapped_column(JSONB)

    # JSONB: diagnostik fra seneste scrape-kørsel (status_code, ekstraktorer, fejltype, m.m.)
    last_diagnostic: Mapped[dict | None] = mapped_column(JSONB)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def owner_name(self) -> str | None:
        if self.owner:
            return self.owner.display_name or self.owner.email
        return None

    # Relations
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id], lazy="select")
    product: Mapped["Product | None"] = relationship(back_populates="watches")
    shop: Mapped["Shop | None"] = relationship(back_populates="watches")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        lazy="select",
    )
    price_events: Mapped[list["PriceEvent"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        lazy="select",
    )
