from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser
from app.database import get_db
from app.models.shop import Shop
from app.models.watch import Watch
from app.schemas.shop import ShopRead, ShopUpdate

router = APIRouter()


@router.get("", response_model=list[ShopRead])
async def list_shops(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Shop]:
    # Watch-tæller pr. shop
    count_sub = (
        select(Watch.shop_id, func.count(Watch.id).label("watch_count"))
        .group_by(Watch.shop_id)
        .subquery()
    )
    stmt = (
        select(Shop, func.coalesce(count_sub.c.watch_count, 0).label("watch_count"))
        .outerjoin(count_sub, Shop.id == count_sub.c.shop_id)
        .order_by(Shop.name)
    )
    rows = (await db.execute(stmt)).all()

    result = []
    for shop, watch_count in rows:
        shop_read = ShopRead.model_validate(shop)
        shop_read.watch_count = watch_count
        result.append(shop_read)
    return result


@router.patch("/{shop_id}", response_model=ShopRead)
async def update_shop(
    shop_id: uuid.UUID,
    body: ShopUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: AdminUser = None,
) -> Shop:
    shop = (await db.execute(select(Shop).where(Shop.id == shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop ikke fundet")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(shop, field, value)

    await db.commit()
    await db.refresh(shop)
    return shop
