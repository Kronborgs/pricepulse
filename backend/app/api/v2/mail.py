"""
SMTP admin endpoints og email preferences.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser
from app.database import get_db
from app.models.smtp_settings import SMTPSettings
from app.services.smtp_service import SMTPService, encrypt_password, decrypt_password, _app_url

logger = structlog.get_logger(__name__)
router = APIRouter()


class SMTPSettingsRead(BaseModel):
    id: int
    is_active: bool
    host: str
    port: int
    use_tls: bool
    username: str
    from_email: str
    from_name: str

    model_config = {"from_attributes": True}


class SMTPSettingsWrite(BaseModel):
    host: str
    port: int = 587
    use_tls: bool = True
    username: str
    password: str  # plain — krypteres ved gemning
    from_email: str
    from_name: str = "PricePulse"


class TestMailRequest(BaseModel):
    to_email: str


class EmailPrefRead(BaseModel):
    notify_price_drop: bool
    notify_back_in_stock: bool
    notify_new_error: bool
    notify_on_change: bool
    digest_enabled: bool
    digest_frequency: str
    digest_day_of_week: int

    model_config = {"from_attributes": True}


class EmailPrefWrite(BaseModel):
    notify_price_drop: bool | None = None
    notify_back_in_stock: bool | None = None
    notify_new_error: bool | None = None
    notify_on_change: bool | None = None
    digest_enabled: bool | None = None
    digest_frequency: str | None = None
    digest_day_of_week: int | None = None


# ── SMTP Settings (admin only) ────────────────────────────────────────────────

@router.get("/admin/smtp")
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = None,
) -> dict:
    row = await db.scalar(select(SMTPSettings).where(SMTPSettings.is_active == True).limit(1))
    if not row:
        return {"configured": False}
    return {"configured": True, "settings": SMTPSettingsRead.model_validate(row)}


@router.put("/admin/smtp")
async def save_smtp_settings(
    body: SMTPSettingsWrite,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = None,
) -> dict:
    # Deaktivér eksisterende
    existing = await db.execute(select(SMTPSettings))
    for row in existing.scalars().all():
        row.is_active = False

    new_cfg = SMTPSettings(
        is_active=True,
        host=body.host,
        port=body.port,
        use_tls=body.use_tls,
        username=body.username,
        password_enc=encrypt_password(body.password),
        from_email=body.from_email,
        from_name=body.from_name,
        updated_by=str(admin.id) if admin else None,
    )
    db.add(new_cfg)
    await db.commit()
    return {"ok": True}


@router.post("/admin/smtp/test")
async def test_smtp(
    body: TestMailRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = None,
) -> dict:
    svc = SMTPService()
    result = await svc.test_connection(db)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Forbindelsesfejl"))

    try:
        await svc.send_email(
            db,
            to_email=body.to_email,
            subject="PricePulse SMTP test",
            body_html="<p>Test-mail fra PricePulse. SMTP fungerer korrekt.</p>",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


# ── Email preferences (current user) ─────────────────────────────────────────

@router.get("/me/email-preferences")
async def get_email_preferences(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    from app.models.email_preference import EmailPreference
    pref = await db.scalar(
        select(EmailPreference).where(EmailPreference.user_id == user.id)
    )
    if not pref:
        return EmailPrefRead(
            notify_price_drop=True,
            notify_back_in_stock=True,
            notify_new_error=False,
            notify_on_change=False,
            digest_enabled=False,
            digest_frequency="weekly",
            digest_day_of_week=0,
        ).model_dump()
    return EmailPrefRead.model_validate(pref).model_dump()


@router.patch("/me/email-preferences")
async def update_email_preferences(
    body: EmailPrefWrite,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    from app.models.email_preference import EmailPreference
    pref = await db.scalar(
        select(EmailPreference).where(EmailPreference.user_id == user.id)
    )
    if not pref:
        pref = EmailPreference(user_id=user.id)
        db.add(pref)

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(pref, k, v)

    await db.commit()
    return {"ok": True}


# ── Test notification email (current user) ────────────────────────────────────

@router.post("/me/email-preferences/test")
async def send_test_notification(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    """
    Send en eksempel-prisfald-e-mail til den loggede brugers email.
    Bruges til at forhåndsvise, hvordan notifikations-e-mails ser ud.
    """
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from app.models.source_price_event import SourcePriceEvent
    from app.services.smtp_service import SMTPService, _render_template
    from app.models.email_queue import EmailQueue

    svc = SMTPService()
    cfg = await svc._get_active_config(db)
    if not cfg:
        raise HTTPException(status_code=400, detail="Ingen aktiv SMTP-konfiguration")

    # Forsøg at finde et rigtigt watch til brugeren som eksempel
    watch = await db.scalar(
        select(ProductWatch)
        .where(ProductWatch.owner_id == user.id)
        .limit(1)
    )

    if watch:
        source = await db.scalar(
            select(WatchSource).where(WatchSource.watch_id == watch.id).limit(1)
        )
        event = await db.scalar(
            select(SourcePriceEvent)
            .where(SourcePriceEvent.watch_id == watch.id)
            .order_by(SourcePriceEvent.recorded_at.desc())
            .limit(1)
        ) if source else None

        watch_name = watch.title or (source.url if source else "Eksempel produkt")
        old_price = float(event.price) * 1.1 if event and event.price else 999.0
        new_price = float(event.price) if event and event.price else 899.0
        currency = event.currency if event and event.currency else "DKK"
        image_url = watch.image_url
        product_url = source.url if source else None
        watch_id = watch.id
        in_stock = event.stock_status == "in_stock" if event else True
    else:
        watch_name = "Eksempel produkt (ACME Widget Pro)"
        old_price = 1299.0
        new_price = 999.0
        currency = "DKK"
        image_url = None
        product_url = None
        watch_id = None
        in_stock = True

    body = _render_template("price_drop.html", {
        "watch_name": watch_name,
        "old_price": f"{old_price:,.0f}".replace(",", "."),
        "new_price": f"{new_price:,.0f}".replace(",", "."),
        "currency": currency,
        "watch_url": f"{_app_url()}/watches/{watch_id}" if watch_id else _app_url(),
        "product_url": product_url or _app_url(),
        "image_url": image_url,
        "in_stock": in_stock,
        "is_test": True,
    })

    item = EmailQueue(
        user_id=user.id,
        email_type="test",
        to_email=user.email,
        subject="[TEST] Prisfald notifikation — PricePulse",
        body_html=body,
    )
    db.add(item)
    await db.commit()
    return {"ok": True}
