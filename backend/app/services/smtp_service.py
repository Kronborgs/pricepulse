"""
SMTPService — email-udsendelse via aiosmtplib med Jinja2-templates.

Gmail-konfiguration:
  host: smtp.gmail.com
  port: 587
  use_tls: True (STARTTLS)
  username: din@gmail.com
  password: app-specifik adgangskode (ikke Google-kodeord)

Kodeord i DB er krypteret med Fernet. Fernet-nøglen kommer fra (prioriteret rækkefølge):
  1. FERNET_KEY env-variabel
  2. /app/data/.fernet.key — auto-genereres og gemmes ved første opstart
  3. Fallback: base64 af SECRET_KEY (kun til dev, ustabil ved SECRET_KEY rotation)

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


_FERNET_KEY_FILE = Path("/app/data/.fernet.key")


def _get_fernet() -> Any:
    """Returner Fernet-instans til kryptering/dekryptering af SMTP-kodeord.

    Nøgle-prioritering:
      1. FERNET_KEY env-variabel (eksplicit sat af bruger)
      2. /app/data/.fernet.key (auto-genereret ved første opstart, stabil)
      3. Fallback til SECRET_KEY (ustabil — ændres nøglen, mistes SMTP)
    """
    from cryptography.fernet import Fernet

    key = settings.fernet_key
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)

    # Auto-generér og gem en stabil nøgle ved første opstart
    if _FERNET_KEY_FILE.exists():
        key = _FERNET_KEY_FILE.read_text().strip()
        logger.debug("fernet.loaded_from_file")
    else:
        key = Fernet.generate_key().decode()
        try:
            _FERNET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            _FERNET_KEY_FILE.write_text(key)
            logger.info("fernet.generated_and_saved", path=str(_FERNET_KEY_FILE))
        except OSError:
            # Kan ikke skrive (f.eks. i test-miljø) — brug midlertidigt
            logger.warning("fernet.could_not_save_key")

    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_password(enc: str) -> str:
    return _get_fernet().decrypt(enc.encode()).decode()


def _is_digest_due(pref: Any, now: datetime) -> bool:
    """Returnér True hvis digest-e-mailen er forfalden for denne præference."""
    if not pref.last_digest_sent_at:
        return True
    from datetime import timedelta
    delta = now - pref.last_digest_sent_at
    freq = pref.digest_frequency
    if freq == "hourly":
        return delta.total_seconds() >= 3600
    if freq == "daily":
        return delta.total_seconds() >= 86400
    if freq == "weekly":
        return delta.days >= 7
    if freq == "monthly":
        return delta.days >= 28
    return False


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
            raise RuntimeError("Ingen aktiv SMTP-konfiguration")

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
            logger.error("mail_fejl", to=to_email, error=repr(exc))
            raise

    def _build_message(
        self,
        from_email: str,
        from_name: str,
        to_email: str,
        subject: str,
        body_html: str,
    ):
        """Byg MIMEMultipart-email med HTML body."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))
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
                    logger.info("email_sendt_fra_koe", to=item.to_email, type=item.email_type)
                except Exception as exc:
                    err = str(exc)
                    item.last_error = err
                    if item.attempts >= _MAX_ATTEMPTS:
                        item.status = "failed"
                    logger.error(
                        "email_koe_fejl",
                        to=item.to_email,
                        type=item.email_type,
                        attempt=item.attempts,
                        error=err,
                    )
                await db.commit()

    async def send_due_digests(self) -> None:
        """
        Kør af APScheduler hvert 30. minut.
        Find notification_rules med rule_type='digest' der er forfaldne og send digest.
        """
        from datetime import timedelta
        from app.database import AsyncSessionLocal
        from app.models.notification_rule import NotificationRule
        from app.models.product_watch import ProductWatch
        from app.models.source_price_event import SourcePriceEvent
        from app.models.watch_source import WatchSource
        from app.models.product import Product
        from app.models.user import User

        async with AsyncSessionLocal() as db:
            config = await self._get_active_config(db)
            if not config:
                return

            now = datetime.now(timezone.utc)
            rules_result = await db.execute(
                select(NotificationRule)
                .where(
                    NotificationRule.rule_type == "digest",
                    NotificationRule.enabled == True,
                )
            )
            rules = rules_result.scalars().all()

            for rule in rules:
                if not _is_digest_due(rule, now):
                    continue

                user = await db.scalar(select(User).where(User.id == rule.user_id))
                if not user or not user.email:
                    continue

                freq = rule.digest_frequency or "daily"
                since = rule.last_digest_sent_at or (now - timedelta(hours=24))

                # Find alle watches for denne bruger
                watches_result = await db.execute(
                    select(ProductWatch).where(
                        ProductWatch.owner_id == rule.user_id,
                        ProductWatch.status.notin_(["archived"]),
                    )
                )
                watches = watches_result.scalars().all()
                if not watches:
                    continue

                watch_ids = [w.id for w in watches]
                total_watches = len(watches)

                # Hent prisbegivenheder siden sidst
                events_result = await db.execute(
                    select(SourcePriceEvent, WatchSource, ProductWatch, Product)
                    .join(WatchSource, WatchSource.id == SourcePriceEvent.source_id)
                    .join(ProductWatch, ProductWatch.id == WatchSource.watch_id)
                    .join(Product, Product.id == ProductWatch.product_id)
                    .where(
                        ProductWatch.id.in_(watch_ids),
                        SourcePriceEvent.created_at > since,
                        SourcePriceEvent.change_type.notin_(["initial"]),
                    )
                    .order_by(SourcePriceEvent.created_at.desc())
                    .limit(50)
                )
                rows = events_result.all()

                # Byg event-liste — filtrér efter regelens produktfilter
                seen: set = set()
                template_events = []
                filter_mode = rule.filter_mode or "all"
                for ev, source, watch, product in rows:
                    key = (source.id, ev.change_type)
                    if key in seen:
                        continue
                    seen.add(key)

                    # Produktfilter
                    if filter_mode == "tags":
                        rule_tags = set(rule.filter_tags or [])
                        product_tags = set(product.tags or [])
                        if not (rule_tags & product_tags):
                            continue
                    elif filter_mode == "products":
                        rule_products = {str(p) for p in (rule.filter_product_ids or [])}
                        if str(product.id) not in rule_products:
                            continue

                    old_p = float(ev.old_price) if ev.old_price else None
                    new_p = float(ev.new_price) if ev.new_price else None
                    template_events.append({
                        "watch_name": watch.name or product.name,
                        "shop": source.shop,
                        "change_type": ev.change_type,
                        "old_price": f"{old_p:,.0f}".replace(",", ".") if old_p else None,
                        "new_price": f"{new_p:,.0f}".replace(",", ".") if new_p else None,
                        "currency": source.last_currency or "DKK",
                        "image_url": product.image_url,
                        "product_url": source.url,
                        "watch_id": str(watch.id),
                        "stock_status": ev.new_stock or source.last_stock_status,
                    })

                freq_labels = {
                    "hourly": "Timevis",
                    "daily": "Daglig",
                    "weekly": "Ugentlig",
                    "monthly": "Månedlig",
                }
                period_label = freq_labels.get(freq, "Periodisk")
                rule_name = rule.name or period_label
                since_fmt = since.strftime("%d/%m/%Y %H:%M")

                # ── Aktuelle priser fra alle shops (altid med i digest) ─────
                cp_result = await db.execute(
                    select(ProductWatch, WatchSource, Product)
                    .join(Product, Product.id == ProductWatch.product_id)
                    .join(WatchSource, WatchSource.watch_id == ProductWatch.id)
                    .where(
                        ProductWatch.owner_id == rule.user_id,
                        ProductWatch.status.notin_(["archived"]),
                        WatchSource.status.notin_(["archived"]),
                        WatchSource.last_price.isnot(None),
                    )
                    .order_by(ProductWatch.id, WatchSource.last_price.asc())
                )
                seen_products: dict = {}
                for pw2, src2, prod2 in cp_result.all():
                    if filter_mode == "tags":
                        if not (set(rule.filter_tags or []) & set(prod2.tags or [])):
                            continue
                    elif filter_mode == "products":
                        if str(prod2.id) not in {str(p) for p in (rule.filter_product_ids or [])}:
                            continue
                    pid = str(prod2.id)
                    if pid not in seen_products:
                        seen_products[pid] = {
                            "name": pw2.name or prod2.name,
                            "image_url": prod2.image_url,
                            "watch_id": str(pw2.id),
                            "shops": [],
                        }
                    seen_products[pid]["shops"].append({
                        "shop": src2.shop,
                        "price": f"{float(src2.last_price):,.0f}".replace(",", "."),
                        "currency": src2.last_currency or "DKK",
                        "url": src2.url,
                        "stock_status": src2.last_stock_status,
                    })
                products_with_prices = list(seen_products.values())

                body = _render_template("digest.html", {
                    "events": template_events,
                    "products_with_prices": products_with_prices,
                    "period_label": rule_name,
                    "since_label": since_fmt,
                    "total_watches": total_watches,
                    "display_name": user.display_name or user.email.split("@")[0],
                })

                await self._enqueue(
                    db, rule.user_id, user.email, "digest",
                    f"{rule_name} digest — PricePulse", body,
                )

                rule.last_digest_sent_at = now
                await db.commit()
                logger.info("digest_koelagt", rule_id=str(rule.id), user_id=str(rule.user_id), events=len(template_events))


smtp_service = SMTPService()
