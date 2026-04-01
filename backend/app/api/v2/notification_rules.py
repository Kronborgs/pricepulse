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
    body: NotificationRuleWrite,
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


@router.delete("/me/notification-rules/{rule_id}", status_code=204)
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
