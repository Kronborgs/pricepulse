from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.watch_source import WatchSource


class SourcePriceEvent(Base):
    """
    Kun ændrings-events for en WatchSource.
    Oprettet ved initial check og ved prisændring/lagerændring.

    change_type: initial | increase | decrease | unavailable | back_in_stock
    """

    __tablename__ = "source_price_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("source_checks.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    new_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    old_stock: Mapped[str | None] = mapped_column(String(100))
    new_stock: Mapped[str | None] = mapped_column(String(100))
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relations
    source: Mapped["WatchSource"] = relationship(back_populates="price_events")
