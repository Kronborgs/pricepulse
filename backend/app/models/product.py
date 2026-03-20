from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, String, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.watch import Watch


class Product(Base, TimestampMixin):
    """
    Valgfrit overordnet produkt der kan gruppere flere watches (fra forskellige butikker).
    Watches kan eksistere uden et tilknyttet Product.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    ean: Mapped[str | None] = mapped_column(String(50), index=True)    # EAN/barcode til auto-matching

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relations
    watches: Mapped[list["Watch"]] = relationship(
        back_populates="product",
        lazy="select",
    )
