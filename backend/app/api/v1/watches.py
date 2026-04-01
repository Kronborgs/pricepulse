from __future__ import annotations

import uuid
from typing import Annotated, List

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AnyUser, SuperOrAdmin, get_current_user
from app.database import get_db
from app.models.user import User
from app.models.watch import Watch
from app.models.shop import Shop
from app.schemas.watch import (
    WatchCreate,
    WatchDetectResult,
    WatchList,
    WatchRead,
    WatchUpdate,
)
from app.services.watch_service import WatchService

logger = structlog.get_logger()
router = APIRouter()


def _is_privileged(user: User) -> bool:
    """Administrator og superuser kan se alle watches."""
    return user.role in ("admin", "superuser")


def _assert_ownership(watch: Watch, user: User) -> None:
    """Kaster 403 hvis en bruger (user-rolle) forsøger at tilgå en watch de ikke ejer."""
    if not _is_privileged(user) and watch.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Ikke tilstrækkelige rettigheder")


@router.get("", response_model=WatchList)
async def list_watches(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    shop_id: uuid.UUID | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    owner_ids: List[uuid.UUID] = Query(default=[]),
) -> WatchList:
    stmt = (
        select(Watch)
        .options(selectinload(Watch.shop), selectinload(Watch.owner))
        .order_by(Watch.created_at.desc())
    )

    # Brugere (user-rolle) ser kun egne watches
    if not _is_privileged(user):
        stmt = stmt.where(Watch.owner_id == user.id)
    elif owner_ids:
        # Admin/superuser kan filtrere på én eller flere ejere
        stmt = stmt.where(Watch.owner_id.in_(owner_ids))

    if status:
        stmt = stmt.where(Watch.status == status)
    if shop_id:
        stmt = stmt.where(Watch.shop_id == shop_id)
    if product_id:
        stmt = stmt.where(Watch.product_id == product_id)
    if search:
        stmt = stmt.where(
            Watch.title.ilike(f"%{search}%") | Watch.url.ilike(f"%{search}%")
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    watches = result.scalars().all()

    return WatchList(items=list(watches), total=total)


@router.get("/{watch_id}", response_model=WatchRead)
async def get_watch(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Watch:
    stmt = (
        select(Watch)
        .where(Watch.id == watch_id)
        .options(selectinload(Watch.shop), selectinload(Watch.owner))
    )
    watch = (await db.execute(stmt)).scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch ikke fundet")
    _assert_ownership(watch, user)
    return watch


@router.post("", response_model=WatchRead, status_code=201)
async def create_watch(
    body: WatchCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Watch:
    service = WatchService(db)
    watch = await service.create_watch(body, owner_id=user.id)

    # Kør første scrape i baggrunden
    background_tasks.add_task(service.trigger_scrape, watch.id)

    # Genindlæs med shop+owner eager-loaded for at undgå MissingGreenlet i response
    stmt = select(Watch).where(Watch.id == watch.id).options(selectinload(Watch.shop), selectinload(Watch.owner))
    watch = (await db.execute(stmt)).scalar_one()

    logger.info("Watch oprettet", watch_id=str(watch.id), url=watch.url)
    return watch


@router.patch("/{watch_id}", response_model=WatchRead)
async def update_watch(
    watch_id: uuid.UUID,
    body: WatchUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Watch:
    stmt = (
        select(Watch)
        .where(Watch.id == watch_id)
        .options(selectinload(Watch.shop), selectinload(Watch.owner))
    )
    watch = (await db.execute(stmt)).scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch ikke fundet")
    _assert_ownership(watch, user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(watch, field, value)

    await db.commit()
    # Genindlæs med relationer efter commit
    watch = (await db.execute(stmt)).scalar_one()
    return watch


@router.delete("/{watch_id}", status_code=204, response_model=None)
async def delete_watch(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> None:
    stmt = select(Watch).where(Watch.id == watch_id)
    watch = (await db.execute(stmt)).scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch ikke fundet")
    _assert_ownership(watch, user)
    await db.delete(watch)
    await db.commit()


@router.post("/{watch_id}/check", response_model=WatchRead)
async def trigger_check(
    watch_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Watch:
    """Manuelt trigger et check for én watch."""
    stmt = (
        select(Watch)
        .where(Watch.id == watch_id)
        .options(selectinload(Watch.shop), selectinload(Watch.owner))
    )
    watch = (await db.execute(stmt)).scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch ikke fundet")
    _assert_ownership(watch, user)

    service = WatchService(db)
    background_tasks.add_task(service.trigger_scrape, watch_id)

    logger.info("Manuelt check triggered", watch_id=str(watch_id))
    return watch


@router.post("/detect", response_model=WatchDetectResult)
async def detect_watch(
    body: WatchCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> WatchDetectResult:
    """
    Forsøger at auto-detektere pris og titel fra en URL
    uden at gemme watch'en. Bruges i 'Tilføj watch' dialogen.
    """
    service = WatchService(db)
    return await service.detect_from_url(body.url)
