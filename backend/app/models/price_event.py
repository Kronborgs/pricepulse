from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.watch import Watch


class PriceEvent(Base):
    """
    Kun ændringshændelser (price_change, stock_change, error, recovered, initial).
    Deduplikeret via dedup_key for at undgå duplikater ved parallel scraping.
    """

    __tablename__ = "price_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # event_type: initial | price_change | stock_change | error | recovered
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Prisdata
    old_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    new_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_delta: Mapped[float | None] = mapped_column(Numeric(10, 2))          # absolut forskel
    price_delta_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))       # procentvis forskel

    # Lagerdata
    old_stock: Mapped[str | None] = mapped_column(String(100))
    new_stock: Mapped[str | None] = mapped_column(String(100))

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Bruges til deduplication - forhindrer duplikate events
    dedup_key: Mapped[str | None] = mapped_column(String(300), unique=True, index=True)

    # Fri metadata (fejlbesked, raw title, etc.)
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relations
    watch: Mapped["Watch"] = relationship(back_populates="price_events")
