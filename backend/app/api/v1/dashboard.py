from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.price_event import PriceEvent
from app.models.price_history import PriceHistory
from app.models.user import User
from app.models.watch import Watch
from app.schemas.shop import DashboardStats, PriceEventRead

router = APIRouter()


def _get_owner_filter(user: User, owner_id: uuid.UUID | None) -> list:
    """Return SQLAlchemy filter list scoped to the correct owner.

    - user / superuser: always own data (owner_id param is ignored)
    - admin: own data unless owner_id is supplied, then that user's data
    """
    if user.role == "admin" and owner_id is not None:
        return [Watch.owner_id == owner_id]
    return [Watch.owner_id == user.id]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
    owner_id: uuid.UUID | None = Query(None),
) -> DashboardStats:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    owner_filter = _get_owner_filter(user, owner_id)

    # Watch counts
    total = (await db.execute(select(func.count(Watch.id)).where(*owner_filter))).scalar_one()
    active = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "active", *owner_filter))
    ).scalar_one()
    errors = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "error", *owner_filter))
    ).scalar_one()
    blocked = (
        await db.execute(select(func.count(Watch.id)).where(Watch.status == "blocked", *owner_filter))
    ).scalar_one()

    # Prisændringer i dag — kun egne events for user-rolle
    watch_id_subq = (
        select(Watch.id).where(*owner_filter).scalar_subquery()
        if owner_filter
        else None
    )

    def _event_filters(*extra):
        fs = [
            PriceEvent.event_type == "price_change",
            PriceEvent.occurred_at >= today_start,
        ]
        if watch_id_subq is not None:
            fs.append(PriceEvent.watch_id.in_(watch_id_subq))
        fs.extend(extra)
        return and_(*fs)

    drops = (
        await db.execute(
            select(func.count(PriceEvent.id)).where(_event_filters(PriceEvent.price_delta < 0))
        )
    ).scalar_one()

    increases = (
        await db.execute(
            select(func.count(PriceEvent.id)).where(_event_filters(PriceEvent.price_delta > 0))
        )
    ).scalar_one()

    checks_stmt = select(func.count(PriceHistory.id)).where(
        PriceHistory.recorded_at >= today_start
    )
    if owner_filter:
        checks_stmt = checks_stmt.where(
            PriceHistory.watch_id.in_(select(Watch.id).where(*owner_filter).scalar_subquery())
        )
    checks_today = (await db.execute(checks_stmt)).scalar_one()

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
    user: User = Depends(get_current_user),
    owner_id: uuid.UUID | None = Query(None),
) -> list[PriceEventRead]:
    owner_filter = _get_owner_filter(user, owner_id)
    stmt = (
        select(PriceEvent)
        .options(
            joinedload(PriceEvent.watch).joinedload(Watch.product)
        )
        .where(PriceEvent.event_type.in_(["price_change", "stock_change"]))
        .order_by(PriceEvent.occurred_at.desc())
        .limit(limit)
    )
    stmt = stmt.join(Watch, PriceEvent.watch_id == Watch.id).where(*owner_filter)
    result = await db.execute(stmt)
    events = list(result.unique().scalars().all())

    out: list[PriceEventRead] = []
    for ev in events:
        watch = ev.watch
        if watch and watch.product:
            title = watch.product.name
            image_url = watch.product.image_url or watch.image_url
        elif watch:
            title = watch.title
            image_url = watch.image_url
        else:
            title = None
            image_url = None
        out.append(
            PriceEventRead(
                id=ev.id,
                watch_id=ev.watch_id,
                event_type=ev.event_type,
                old_price=float(ev.old_price) if ev.old_price is not None else None,
                new_price=float(ev.new_price) if ev.new_price is not None else None,
                price_delta=float(ev.price_delta) if ev.price_delta is not None else None,
                price_delta_pct=float(ev.price_delta_pct) if ev.price_delta_pct is not None else None,
                old_stock=ev.old_stock,
                new_stock=ev.new_stock,
                occurred_at=ev.occurred_at,
                extra_data=ev.extra_data,
                watch_title=title,
                watch_image_url=image_url,
            )
        )
    return out
