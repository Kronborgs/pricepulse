from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product_watch import ProductWatch


class ProductSnapshot(Base):
    """
    Aggregeret prissnapshot for et ProductWatch.
    Beregnes periodisk af scheduleren (fx hvert 6. check eller 1x/time).
    Bruges til produktniveau-grafer: best/avg/min/max price over tid.
    """

    __tablename__ = "product_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_watches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    best_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    best_price_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="SET NULL"), nullable=True
    )
    avg_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    min_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    max_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    shops_with_stock: Mapped[int | None] = mapped_column(Integer)
    active_shops: Mapped[int | None] = mapped_column(Integer)

    # Relations
    watch: Mapped["ProductWatch"] = relationship(back_populates="snapshots")
