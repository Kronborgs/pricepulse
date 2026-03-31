"""
SMTPService — email-udsendelse via aiosmtplib med Jinja2-templates.

Gmail-konfiguration:
  host: smtp.gmail.com
  port: 587
  use_tls: True (STARTTLS)
  username: din@gmail.com
  password: app-specifik adgangskode (ikke Google-kodeord)

Kodeord i DB er krypteret med Fernet. Fernet-nøglen kommer fra:
  settings.fernet_key — sæt i .env fil
  Fallback: base64 af settings.secret_key (kun til dev)

Design:
  - send_pending_emails() køres af APScheduler hvert 5. min
  - Max 3 forsøg pr. mail
  - Jinja2-templates i backend/app/templates/email/
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = structlog.get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
_MAX_ATTEMPTS = 3


def _app_url() -> str:
    """Frontend base-URL: frontend_url har forrang, ellers første cors_origins-værdi."""
    if settings.frontend_url.strip():
        return settings.frontend_url.strip().rstrip("/")
    for origin in settings.cors_origins.split(","):
        origin = origin.strip()
        if origin.startswith("http"):
            return origin.rstrip("/")
    return ""


def _get_fernet() -> Any:
    """Returner Fernet-instans til kryptering/dekryptering af SMTP-kodeord."""
    from cryptography.fernet import Fernet
    key = settings.fernet_key
    if not key:
        # Fallback: brug secret_key paddet til 32 bytes → base64url
        raw = settings.secret_key.encode()[:32].ljust(32, b"0")
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_password(enc: str) -> str:
    return _get_fernet().decrypt(enc.encode()).decode()


def _render_template(name: str, context: dict) -> str:
    """Render Jinja2-template. Returnerer fallback-tekst hvis template ikke findes."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        tpl = env.get_template(name)
        base = _app_url()
        merged = {
            "app_url": base,
            "logo_url": f"{base}/logo.png",
            **context,
        }
        return tpl.render(**merged)
    except Exception:
        # Fallback til plain text
        return str(context)


class SMTPService:
    async def _get_active_config(self, db: AsyncSession):
        """Hent aktiv SMTP-konfiguration fra DB."""
        from app.models.smtp_settings import SMTPSettings
        result = await db.scalar(
            select(SMTPSettings).where(SMTPSettings.is_active == True).limit(1)
        )
        return result

    async def send_email(
        self,
        db: AsyncSession,
        to_email: str,
        subject: str,
        body_html: str,
    ) -> bool:
        """Send email direkte. Returnerer True ved succes."""
        config = await self._get_active_config(db)
        if not config:
            logger.warning("smtp_ingen_konfiguration")
            return False

        try:
            import aiosmtplib
            password = decrypt_password(config.password_enc)
            msg = self._build_message(
                from_email=config.from_email,
                from_name=config.from_name,
                to_email=to_email,
                subject=subject,
                body_html=body_html,
            )
            await aiosmtplib.send(
                msg,
                hostname=config.host,
                port=config.port,
                start_tls=config.use_tls,
                username=config.username,
                password=password,
            )
            logger.info("mail_sendt", to=to_email, subject=subject)
            return True
        except Exception as exc:
            logger.error("mail_fejl", to=to_email, error=str(exc))
            raise

    def _build_message(
        self,
        from_email: str,
        from_name: str,
        to_email: str,
        subject: str,
        body_html: str,
    ):
        """Byg email.message.EmailMessage med HTML body."""
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_type("text/html")
        msg.set_payload(body_html, charset="utf-8")
        return msg

    async def test_connection(self, db: AsyncSession) -> dict:
        """Test SMTP-forbindelsen uden at sende mail. Bruges fra admin UI."""
        config = await self._get_active_config(db)
        if not config:
            return {"ok": False, "error": "Ingen aktiv SMTP-konfiguration"}
        try:
            import aiosmtplib
            password = decrypt_password(config.password_enc)
            smtp = aiosmtplib.SMTP(
                hostname=config.host,
                port=config.port,
                start_tls=config.use_tls,
            )
            await smtp.connect()
            await smtp.login(config.username, password)
            await smtp.quit()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Queue helpers ─────────────────────────────────────────────────────────

    async def queue_welcome(self, db: AsyncSession, user: Any) -> None:
        """Kø velkomstmail til ny bruger."""
        body = _render_template("welcome.html", {
            "display_name": user.display_name or user.email,
        })
        await self._enqueue(db, user.id, user.email, "welcome", "Velkommen til PricePulse", body)

    async def queue_password_reset(self, db: AsyncSession, email: str, token: str) -> None:
        """Kø password-reset mail."""
        from sqlalchemy import select
        from app.models.user import User
        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            return

        reset_url = f"{settings.cors_origins.split(',')[0]}/reset-password?token={token}"
        body = _render_template("password_reset.html", {
            "display_name": user.display_name or user.email,
            "reset_url": reset_url,
        })
        await self._enqueue(
            db, user.id, user.email, "password_reset",
            "Nulstil dit kodeord — PricePulse", body
        )

    async def queue_price_drop(
        self, db: AsyncSession, user_id: uuid.UUID, to_email: str,
        watch_name: str, old_price: float, new_price: float,
        currency: str, watch_id: uuid.UUID, source_id: uuid.UUID | None = None,
        image_url: str | None = None, product_url: str | None = None,
        in_stock: bool = True,
    ) -> None:
        body = _render_template("price_drop.html", {
            "watch_name": watch_name,
            "old_price": f"{old_price:,.0f}".replace(",", "."),
            "new_price": f"{new_price:,.0f}".replace(",", "."),
            "currency": currency,
            "watch_url": f"{settings.cors_origins.split(',')[0]}/watches/{watch_id}",
            "product_url": product_url,
            "image_url": image_url,
            "in_stock": in_stock,
            "is_test": False,
        })
        await self._enqueue(
            db, user_id, to_email, "price_drop",
            f"Prisfald: {watch_name} — PricePulse", body,
            related_watch_id=watch_id, related_source_id=source_id,
        )

    async def _enqueue(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        to_email: str,
        email_type: str,
        subject: str,
        body_html: str,
        related_watch_id: uuid.UUID | None = None,
        related_source_id: uuid.UUID | None = None,
    ) -> None:
        from app.models.email_queue import EmailQueue
        item = EmailQueue(
            user_id=user_id,
            email_type=email_type,
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            related_watch_id=related_watch_id,
            related_source_id=related_source_id,
        )
        db.add(item)
        await db.commit()

    # ── APScheduler job ───────────────────────────────────────────────────────

    async def send_pending_emails(self) -> None:
        """
        Kør af APScheduler hvert 5. minut.
        Sender pending mails fra email_queue — max 3 forsøg.
        """
        from app.database import AsyncSessionLocal
        from app.models.email_queue import EmailQueue
        async with AsyncSessionLocal() as db:
            config = await self._get_active_config(db)
            if not config:
                return

            now = datetime.now(timezone.utc)
            items = await db.execute(
                select(EmailQueue).where(
                    EmailQueue.status == "pending",
                    EmailQueue.scheduled_for <= now,
                    EmailQueue.attempts < _MAX_ATTEMPTS,
                ).limit(20)
            )
            rows = items.scalars().all()

            for item in rows:
                item.attempts += 1
                try:
                    await self.send_email(db, item.to_email, item.subject or "", item.body_html or "")
                    item.status = "sent"
                    item.sent_at = datetime.now(timezone.utc)
                except Exception:
                    if item.attempts >= _MAX_ATTEMPTS:
                        item.status = "failed"
                await db.commit()


smtp_service = SMTPService()
