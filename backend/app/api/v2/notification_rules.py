"""
Notification rules — per-bruger notifikationsregler med produktfiltre og intervaller.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.config import settings
from app.database import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()

_VALID_RULE_TYPES = {"instant", "digest"}
_VALID_FILTER_MODES = {"all", "tags", "products"}
_VALID_FREQUENCIES = {"hourly", "daily", "weekly", "monthly"}


class NotificationRuleRead(BaseModel):
    id: str
    name: str | None
    enabled: bool
    rule_type: str
    notify_price_drop: bool
    notify_back_in_stock: bool
    notify_on_change: bool
    notify_new_error: bool
    filter_mode: str
    filter_tags: list[str] | None
    filter_product_ids: list[str] | None
    digest_frequency: str | None
    digest_day_of_week: int | None
    last_digest_sent_at: str | None = None

    model_config = {"from_attributes": True}


class NotificationRuleWrite(BaseModel):
    name: str | None = None
    enabled: bool = True
    rule_type: str
    notify_price_drop: bool = True
    notify_back_in_stock: bool = True
    notify_on_change: bool = False
    notify_new_error: bool = False
    filter_mode: str = "all"
    filter_tags: list[str] | None = None
    filter_product_ids: list[str] | None = None  # UUIDs som strenge
    digest_frequency: str | None = None
    digest_day_of_week: int | None = None

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in _VALID_RULE_TYPES:
            raise ValueError(f"rule_type skal være en af: {_VALID_RULE_TYPES}")
        return v

    @field_validator("filter_mode")
    @classmethod
    def validate_filter_mode(cls, v: str) -> str:
        if v not in _VALID_FILTER_MODES:
            raise ValueError(f"filter_mode skal være en af: {_VALID_FILTER_MODES}")
        return v

    @field_validator("digest_frequency")
    @classmethod
    def validate_digest_frequency(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_FREQUENCIES:
            raise ValueError(f"digest_frequency skal være en af: {_VALID_FREQUENCIES}")
        return v


class NotificationRulePatch(BaseModel):
    """Partial update — alle felter er valgfrie (bruges til PATCH)."""
    name: str | None = None
    enabled: bool | None = None
    rule_type: str | None = None
    notify_price_drop: bool | None = None
    notify_back_in_stock: bool | None = None
    notify_on_change: bool | None = None
    notify_new_error: bool | None = None
    filter_mode: str | None = None
    filter_tags: list[str] | None = None
    filter_product_ids: list[str] | None = None
    digest_frequency: str | None = None
    digest_day_of_week: int | None = None

    @field_validator("rule_type", mode="before")
    @classmethod
    def validate_rule_type(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_RULE_TYPES:
            raise ValueError(f"rule_type skal være en af: {_VALID_RULE_TYPES}")
        return v

    @field_validator("filter_mode", mode="before")
    @classmethod
    def validate_filter_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_FILTER_MODES:
            raise ValueError(f"filter_mode skal være en af: {_VALID_FILTER_MODES}")
        return v

    @field_validator("digest_frequency", mode="before")
    @classmethod
    def validate_digest_frequency(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_FREQUENCIES:
            raise ValueError(f"digest_frequency skal være en af: {_VALID_FREQUENCIES}")
        return v


def _serialize_rule(rule: Any) -> dict:
    return {
        "id": str(rule.id),
        "name": rule.name,
        "enabled": rule.enabled,
        "rule_type": rule.rule_type,
        "notify_price_drop": rule.notify_price_drop,
        "notify_back_in_stock": rule.notify_back_in_stock,
        "notify_on_change": rule.notify_on_change,
        "notify_new_error": rule.notify_new_error,
        "filter_mode": rule.filter_mode,
        "filter_tags": rule.filter_tags,
        "filter_product_ids": [str(p) for p in rule.filter_product_ids] if rule.filter_product_ids else None,
        "digest_frequency": rule.digest_frequency,
        "digest_day_of_week": rule.digest_day_of_week,
        "last_digest_sent_at": rule.last_digest_sent_at.isoformat() if rule.last_digest_sent_at else None,
    }


@router.get("/me/notification-rules")
async def list_notification_rules(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> list[dict]:
    from app.models.notification_rule import NotificationRule
    result = await db.execute(
        select(NotificationRule)
        .where(NotificationRule.user_id == user.id)
        .order_by(NotificationRule.created_at.asc())
    )
    return [_serialize_rule(r) for r in result.scalars().all()]


@router.post("/me/notification-rules", status_code=201)
async def create_notification_rule(
    body: NotificationRuleWrite,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    from app.models.notification_rule import NotificationRule
    rule = NotificationRule(
        user_id=user.id,
        name=body.name,
        enabled=body.enabled,
        rule_type=body.rule_type,
        notify_price_drop=body.notify_price_drop,
        notify_back_in_stock=body.notify_back_in_stock,
        notify_on_change=body.notify_on_change,
        notify_new_error=body.notify_new_error,
        filter_mode=body.filter_mode,
        filter_tags=body.filter_tags or None,
        filter_product_ids=(
            [uuid.UUID(p) for p in body.filter_product_ids]
            if body.filter_product_ids else None
        ),
        digest_frequency=body.digest_frequency,
        digest_day_of_week=body.digest_day_of_week,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    logger.info("notification_rule_oprettet", rule_id=str(rule.id), user_id=str(user.id))
    return _serialize_rule(rule)


@router.patch("/me/notification-rules/{rule_id}")
async def update_notification_rule(
    rule_id: uuid.UUID,
    body: NotificationRulePatch,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    from app.models.notification_rule import NotificationRule
    rule = await db.scalar(
        select(NotificationRule).where(
            NotificationRule.id == rule_id,
            NotificationRule.user_id == user.id,
        )
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regel ikke fundet")

    data = body.model_dump(exclude_unset=True)
    if "filter_product_ids" in data and data["filter_product_ids"] is not None:
        data["filter_product_ids"] = [uuid.UUID(p) for p in data["filter_product_ids"]]
    if "filter_tags" in data and data["filter_tags"] == []:
        data["filter_tags"] = None

    # Reset last_digest_sent_at if frequency changes so digest fires promptly
    if "digest_frequency" in data and data["digest_frequency"] != rule.digest_frequency:
        rule.last_digest_sent_at = None

    for k, v in data.items():
        setattr(rule, k, v)

    await db.commit()
    await db.refresh(rule)
    return _serialize_rule(rule)


@router.post("/me/notification-rules/{rule_id}/run")
async def run_notification_rule_now(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    """
    Kør en notifikationsregel med det samme — omgår scheduler-timing.
    Digest: sender rigtig digest-email via køen (ankommer inden for 5 min).
    Instant: sender en price_drop-email for et tilfældigt matchende produkt.
    Opdaterer last_digest_sent_at og returnerer den opdaterede regel.
    """
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    from app.models.notification_rule import NotificationRule
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from app.models.product import Product
    from app.models.source_price_event import SourcePriceEvent
    from app.models.user import User
    from app.services.smtp_service import smtp_service, _render_template
    from sqlalchemy import func, nullslast
    _TZ = ZoneInfo("Europe/Copenhagen")

    rule = await db.scalar(
        select(NotificationRule).where(
            NotificationRule.id == rule_id,
            NotificationRule.user_id == user.id,
        )
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regel ikke fundet")

    cfg = await smtp_service._get_active_config(db)
    if not cfg:
        raise HTTPException(
            status_code=400,
            detail="Ingen aktiv SMTP-konfiguration — konfigurer SMTP under Admin → SMTP",
        )

    owner = await db.scalar(select(User).where(User.id == user.id))
    if not owner or not owner.email:
        raise HTTPException(status_code=400, detail="Brugeren har ingen email-adresse")

    rule_label = rule.name or ("Digest" if rule.rule_type == "digest" else "Øjeblikkelig")
    now = datetime.now(timezone.utc)

    if rule.rule_type == "digest":
        # ── Kør digest-logik for netop denne regel ────────────────────────────
        since = rule.last_digest_sent_at or (now - timedelta(days=30))

        watches_result = await db.execute(
            select(ProductWatch).where(
                ProductWatch.owner_id == user.id,
                ProductWatch.status.notin_(["archived"]),
            )
        )
        watches = watches_result.scalars().all()
        watch_ids = [w.id for w in watches]

        template_events: list[dict] = []
        if watch_ids:
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
            seen: set = set()
            for ev, source, watch, product in rows:
                key = (source.id, ev.change_type)
                if key in seen:
                    continue
                seen.add(key)
                filter_mode = rule.filter_mode or "all"
                if filter_mode == "tags":
                    if not (set(rule.filter_tags or []) & set(product.tags or [])):
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

        # ── Aktuelle priser fra alle shops (uanset om der er ændringer) ───────
        cp_result = await db.execute(
            select(ProductWatch, WatchSource, Product)
            .join(Product, Product.id == ProductWatch.product_id)
            .join(WatchSource, WatchSource.watch_id == ProductWatch.id)
            .where(
                ProductWatch.owner_id == user.id,
                ProductWatch.status.notin_(["archived"]),
                WatchSource.status.notin_(["archived"]),
            )
            .order_by(ProductWatch.id, nullslast(WatchSource.last_price.asc()))
        )
        seen_products: dict = {}
        for pw2, src2, prod2 in cp_result.all():
            pid = str(prod2.id)
            if pid not in seen_products:
                seen_products[pid] = {
                    "name": pw2.name or prod2.name,
                    "image_url": prod2.image_url,
                    "watch_id": str(pw2.id),
                    "shops": [],
                }
            price_raw = float(src2.last_price) if src2.last_price is not None else None
            lca = src2.last_check_at
            seen_products[pid]["shops"].append({
                "shop": src2.shop,
                "price": f"{price_raw:,.0f}".replace(",", ".") if price_raw is not None else "—",
                "price_raw": price_raw,
                "currency": src2.last_currency or "DKK",
                "url": src2.url,
                "stock_status": src2.last_stock_status,
                "last_check_at": lca.astimezone(_TZ).isoformat() if lca else None,
            })
        # Markér billigste shop per produkt
        for prod_data in seen_products.values():
            shops = prod_data["shops"]
            priced = [s for s in shops if s["price_raw"] is not None]
            if priced:
                min_price = min(s["price_raw"] for s in priced)
                for s in shops:
                    s["cheapest"] = (s["price_raw"] is not None and s["price_raw"] == min_price)
            else:
                for s in shops:
                    s["cheapest"] = False
        products_with_prices = list(seen_products.values())

        body_html = _render_template("digest.html", {
            "events": template_events,
            "products_with_prices": products_with_prices,
            "period_label": rule_label,
            "since_label": since.astimezone(_TZ).strftime("%d/%m/%Y %H:%M"),
            "total_watches": len(watches),
            "display_name": owner.display_name or owner.email.split("@")[0],
        })

        # Send direkte — omgår køen så mailen ankommer med det samme
        await smtp_service.send_email(
            db, owner.email,
            f"{rule_label} digest — PricePulse",
            body_html,
        )
        rule.last_digest_sent_at = now
        await db.commit()
        await db.refresh(rule)
        logger.info("digest_sendt_manuelt", rule_id=str(rule.id), user_id=str(user.id), events=len(template_events), products=len(products_with_prices))

    else:
        # ── Kør instant for netop denne regel med et tilfældigt produkt ───────
        row = await db.execute(
            select(ProductWatch, WatchSource, Product)
            .join(Product, Product.id == ProductWatch.product_id)
            .join(WatchSource, WatchSource.watch_id == ProductWatch.id)
            .where(
                ProductWatch.owner_id == user.id,
                WatchSource.last_price.isnot(None),
            )
            .order_by(func.random())
            .limit(1)
        )
        ex = row.first()
        if ex:
            pw, source, product = ex
            prev = await db.scalar(
                select(SourcePriceEvent)
                .where(
                    SourcePriceEvent.source_id == source.id,
                    SourcePriceEvent.old_price.isnot(None),
                )
                .order_by(SourcePriceEvent.created_at.desc())
                .limit(1)
            )
            old_price_val = float(prev.old_price) if prev else round(float(source.last_price) * 1.15, 0)
            # Send direkte — omgår køen så mailen ankommer med det samme
            body_html = _render_template("price_drop.html", {
                "watch_name": pw.name or product.name,
                "old_price": f"{old_price_val:,.0f}".replace(",", "."),
                "new_price": f"{float(source.last_price):,.0f}".replace(",", "."),
                "currency": source.last_currency or "DKK",
                "watch_url": f"{settings.cors_origins.split(',')[0]}/watches/{pw.id}",
                "product_url": source.url,
                "image_url": product.image_url,
                "in_stock": True,
                "is_test": False,
            })
            await smtp_service.send_email(
                db, owner.email,
                f"Prisfald: {pw.name or product.name} — PricePulse",
                body_html,
            )
        else:
            # Ingen produkter med kendte priser — send plain besked
            await smtp_service.send_email(
                db, owner.email,
                f"{rule_label} — PricePulse",
                "<p style='font-family:sans-serif'>Ingen produkter matcher denne regel endnu.</p>",
            )
        logger.info("instant_sendt_manuelt", rule_id=str(rule.id), user_id=str(user.id))

    return _serialize_rule(rule)


@router.delete("/me/notification-rules/{rule_id}", status_code=204, response_model=None)
async def delete_notification_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> None:
    from app.models.notification_rule import NotificationRule
    rule = await db.scalar(
        select(NotificationRule).where(
            NotificationRule.id == rule_id,
            NotificationRule.user_id == user.id,
        )
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regel ikke fundet")
    await db.delete(rule)
    await db.commit()
