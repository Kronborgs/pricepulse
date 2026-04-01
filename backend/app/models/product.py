from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.product_watch import ProductWatch
    from app.models.user import User
    from app.models.watch import Watch


class Product(Base, TimestampMixin):
    """
    Produkt-entiteten. Kan normaliseres via Ollama.
    Grupperer ProductWatch-instanser (v2) og legacy Watch-instanser (v1).
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Ejerskab (hvem oprettede produktet)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(300))
    variant: Mapped[str | None] = mapped_column(String(200))
    mpn: Mapped[str | None] = mapped_column(String(100), index=True)           # manufacturer part number
    ean: Mapped[str | None] = mapped_column(String(50), index=True)            # EAN/barcode
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    # active | paused | archived
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Bruger-definerede tags (fx "lego", "akvarie", "cpu")
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)

    # Ollama normalisering
    ollama_normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalization_confidence: Mapped[float | None] = mapped_column(Float)
    normalization_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relations — v2
    product_watches: Mapped[list["ProductWatch"]] = relationship(
        back_populates="product",
        lazy="select",
    )
    # Ejerskab
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id], lazy="select")

    @property
    def owner_name(self) -> str | None:
        if self.owner:
            return self.owner.display_name or self.owner.email
        return None

    # Relations — v1 legacy
    watches: Mapped[list["Watch"]] = relationship(
        back_populates="product",
        lazy="select",
    )
