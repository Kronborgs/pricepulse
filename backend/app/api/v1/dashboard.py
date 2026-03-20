from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.price_event import PriceEvent
from app.models.price_history import PriceHistory
from app.models.watch import Watch
from app.schemas.shop import DashboardStats, PriceEventRead

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardStats:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Watch counts
    total = (await db.execute(select(func.count(Watch.id)))).scalar_one()
    active = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "active"))
    ).scalar_one()
    errors = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "error"))
    ).scalar_one()
    blocked = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "blocked"))
    ).scalar_one()

    # Prisændringer i dag
    drops = (
        await db.execute(
            select(func.count(PriceEvent.id)).where(
                and_(
                    PriceEvent.event_type == "price_change",
                    PriceEvent.occurred_at >= today_start,
                    PriceEvent.price_delta < 0,
                )
            )
        )
    ).scalar_one()

    increases = (
        await db.execute(
            select(func.count(PriceEvent.id)).where(
                and_(
                    PriceEvent.event_type == "price_change",
                    PriceEvent.occurred_at >= today_start,
                    PriceEvent.price_delta > 0,
                )
            )
        )
    ).scalar_one()

    checks_today = (
        await db.execute(
            select(func.count(PriceHistory.id)).where(
                PriceHistory.recorded_at >= today_start
            )
        )
    ).scalar_one()

    return DashboardStats(
        total_watches=total,
        active_watches=active,
        error_watches=errors,
        blocked_watches=blocked,
        price_drops_today=drops,
        price_increases_today=increases,
        checks_today=checks_today,
        total_products=0,
    )


@router.get("/recent-events", response_model=list[PriceEventRead])
async def get_recent_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
) -> list[PriceEvent]:
    stmt = (
        select(PriceEvent)
        .where(PriceEvent.event_type.in_(["price_change", "stock_change"]))
        .order_by(PriceEvent.occurred_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
