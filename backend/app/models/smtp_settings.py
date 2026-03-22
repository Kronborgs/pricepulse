from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SMTPSettings(Base):
    """
    SMTP-konfiguration til mail-udsendelse.
    Kun én aktiv konfiguration ad gangen (is_active=True).

    Kodeordet er krypteret med Fernet (APP_FERNET_KEY fra env).
    Gmail: host=smtp.gmail.com, port=587, use_tls=True
    Brug app-specifik adgangskode — ikke Google-kontens kodeord.
    """

    __tablename__ = "smtp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-krypteret
    from_email: Mapped[str] = mapped_column(Text, nullable=False)
    from_name: Mapped[str] = mapped_column(Text, default="PricePulse", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(String(36), nullable=True)
