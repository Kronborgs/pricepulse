from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product_watch import ProductWatch
    from app.models.source_check import SourceCheck
    from app.models.source_price_event import SourcePriceEvent


class WatchSource(Base, TimestampMixin):
    """
    En konkret webshop-URL der overvåges som del af et ProductWatch.
    Har sin egen status, interval-override og check-historik.

    Status:
      pending  → aldrig tjekket
      active   → kører normalt
      paused   → sat på pause af brugeren
      error    → gentagne fejl (consecutive_errors >= threshold)
      blocked  → bot-beskyttelse eller 403/429
      archived → arkiveret (soft-delete)
    """

    __tablename__ = "watch_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_watches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shop: Mapped[str] = mapped_column(Text, nullable=False)                  # computersalg.dk
    url: Mapped[str] = mapped_column(Text, nullable=False)
    previous_url: Mapped[str | None] = mapped_column(Text)                   # gem ved URL-ændring
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    interval_override_min: Mapped[int | None] = mapped_column(Integer)       # None = brug watch default
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    last_currency: Mapped[str] = mapped_column(String(3), default="DKK", nullable=False)
    last_stock_status: Mapped[str | None] = mapped_column(String(100))
    last_error_type: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    last_diagnostic: Mapped[dict | None] = mapped_column(JSONB)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bot_suspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(50), default="http", nullable=False)
    scraper_config: Mapped[dict | None] = mapped_column(JSONB)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relations
    watch: Mapped["ProductWatch"] = relationship(
        back_populates="sources",
        foreign_keys="WatchSource.watch_id",
        lazy="select",
    )
    checks: Mapped[list["SourceCheck"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="select",
    )
    price_events: Mapped[list["SourcePriceEvent"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="select",
    )
