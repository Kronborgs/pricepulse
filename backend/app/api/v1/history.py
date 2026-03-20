from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.price_history import PriceHistory
from app.models.price_event import PriceEvent
from app.schemas.shop import PriceHistoryPoint, PriceEventRead

router = APIRouter()


@router.get("/watches/{watch_id}/prices", response_model=list[PriceHistoryPoint])
async def get_price_history(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(500, ge=1, le=5000),
    since: datetime | None = Query(None),
) -> list[PriceHistory]:
    stmt = (
        select(PriceHistory)
        .where(PriceHistory.watch_id == watch_id)
        .order_by(PriceHistory.recorded_at.asc())
        .limit(limit)
    )
    if since:
        stmt = stmt.where(PriceHistory.recorded_at >= since)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/watches/{watch_id}/events", response_model=list[PriceEventRead])
async def get_watch_events(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=500),
) -> list[PriceEvent]:
    stmt = (
        select(PriceEvent)
        .where(PriceEvent.watch_id == watch_id)
        .order_by(PriceEvent.occurred_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
