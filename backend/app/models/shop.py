from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.watch import Watch


class Shop(Base, TimestampMixin):
    """En webshop der kan overvåges."""

    __tablename__ = "shops"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(Text)

    # Scraper-konfiguration pr. shop
    default_provider: Mapped[str] = mapped_column(String(50), default="curl_cffi")
    default_price_selector: Mapped[str | None] = mapped_column(Text)
    default_title_selector: Mapped[str | None] = mapped_column(Text)
    default_stock_selector: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relations
    watches: Mapped[list["Watch"]] = relationship(
        back_populates="shop",
        lazy="select",
    )
