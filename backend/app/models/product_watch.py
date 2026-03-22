from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.product_snapshot import ProductSnapshot
    from app.models.watch_source import WatchSource
    from app.models.watch_timeline_event import WatchTimelineEvent
    from app.models.user import User


class ProductWatch(Base, TimestampMixin):
    """
    Brugerens overvågningsopsætning for ét produkt.
    Ét produkt kan have én ProductWatch med flere WatchSource URLs.

    Status:
      pending  → oprettet, aldrig tjekket
      active   → mindst én source kører normalt
      partial  → blanding af aktive og fejlende/pausede sources
      paused   → hele watch er sat på pause af brugeren
      error    → alle sources fejler
      archived → watch er arkiveret (soft-delete)
    """

    __tablename__ = "product_watches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(Text)
    default_interval_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    last_best_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    last_best_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "watch_sources.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_product_watches_last_best_source",
        ),
        nullable=True,
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Notifikationsindstillinger pr. watch
    notify_on_price_drop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_back_in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price_threshold: Mapped[float | None] = mapped_column(Numeric(10, 2))  # notify kun hvis under

    # Relations
    product: Mapped["Product"] = relationship(
        back_populates="product_watches",
        lazy="select",
    )
    owner: Mapped["User | None"] = relationship(
        foreign_keys="ProductWatch.owner_id",
        lazy="select",
    )
    sources: Mapped[list["WatchSource"]] = relationship(
        back_populates="watch",
        foreign_keys="WatchSource.watch_id",
        cascade="all, delete-orphan",
        lazy="select",
    )
    snapshots: Mapped[list["ProductSnapshot"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        lazy="select",
    )
    timeline: Mapped[list["WatchTimelineEvent"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        lazy="select",
    )
    last_best_source: Mapped["WatchSource | None"] = relationship(
        foreign_keys=[last_best_source_id],
        lazy="select",
        viewonly=True,
    )
