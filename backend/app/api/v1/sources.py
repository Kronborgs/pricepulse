"""
API v1 — Sources (WatchSource CRUD)

Endpoints til håndtering af individuelle webshop-URLs tilknyttet et ProductWatch.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product_watch import ProductWatch
from app.models.source_check import SourceCheck
from app.models.source_price_event import SourcePriceEvent
from app.models.user import User
from app.models.watch_source import WatchSource
from app.models.watch_timeline_event import WatchTimelineEvent
from app.schemas.v2 import (
    ProductWatchCreate,
    ProductWatchList,
    ProductWatchRead,
    ProductWatchUpdate,
    SourceCheckList,
    SourceCheckRead,
    SourcePriceEventRead,
    TimelineEventRead,
    WatchSourceCreate,
    WatchSourceRead,
    WatchSourceUpdate,
)
from app.services.source_service import SourceService

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_watch_or_404(watch_id: uuid.UUID, db: AsyncSession) -> ProductWatch:
    stmt = (
        select(ProductWatch)
        .where(ProductWatch.id == watch_id)
        .options(selectinload(ProductWatch.sources))
    )
    watch = (await db.execute(stmt)).scalar_one_or_none()
    if not watch:
        raise HTTPException(status_code=404, detail="ProductWatch ikke fundet")
    return watch


def _assert_watch_ownership(watch: ProductWatch, user: User) -> None:
    """Kaster 403 hvis bruger (user-rolle) ikke ejer watch'en."""
    if user.role not in ("admin", "superuser") and watch.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Ikke tilstrækkelige rettigheder")


async def _get_source_or_404(source_id: uuid.UUID, db: AsyncSession) -> WatchSource:
    stmt = (
        select(WatchSource)
        .where(WatchSource.id == source_id)
        .options(selectinload(WatchSource.watch))
    )
    source = (await db.execute(stmt)).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="WatchSource ikke fundet")
    return source


# ── ProductWatch endpoints ────────────────────────────────────────────────────

@router.get("/product-watches", response_model=ProductWatchList, tags=["product-watches"])
async def list_product_watches(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
) -> ProductWatchList:
    stmt = (
        select(ProductWatch)
        .options(selectinload(ProductWatch.sources))
        .order_by(ProductWatch.created_at.desc())
    )
    # Brugere (user-rolle) ser kun egne watches
    if user.role not in ("admin", "superuser"):
        stmt = stmt.where(ProductWatch.owner_id == user.id)
    if status:
        stmt = stmt.where(ProductWatch.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.offset(skip).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    return ProductWatchList(items=list(items), total=total)


@router.get("/product-watches/{watch_id}", response_model=ProductWatchRead, tags=["product-watches"])
async def get_product_watch(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> ProductWatch:
    watch = await _get_watch_or_404(watch_id, db)
    _assert_watch_ownership(watch, user)
    return watch


@router.post("/product-watches/{watch_id}/pause", response_model=ProductWatchRead, tags=["product-watches"])
async def pause_product_watch(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> ProductWatch:
    watch = await _get_watch_or_404(watch_id, db)
    _assert_watch_ownership(watch, user)
    svc = SourceService(db)
    return await svc.pause_watch(watch)


@router.post("/product-watches/{watch_id}/resume", response_model=ProductWatchRead, tags=["product-watches"])
async def resume_product_watch(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> ProductWatch:
    watch = await _get_watch_or_404(watch_id, db)
    _assert_watch_ownership(watch, user)
    svc = SourceService(db)
    return await svc.resume_watch(watch)


@router.patch("/product-watches/{watch_id}", response_model=ProductWatchRead, tags=["product-watches"])
async def update_product_watch(
    watch_id: uuid.UUID,
    body: ProductWatchUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> ProductWatch:
    watch = await _get_watch_or_404(watch_id, db)
    _assert_watch_ownership(watch, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(watch, field, value)
    await db.commit()
    await db.refresh(watch)
    return watch


@router.get("/product-watches/{watch_id}/timeline", response_model=list[TimelineEventRead], tags=["product-watches"])
async def get_watch_timeline(
    watch_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=500),
) -> list[WatchTimelineEvent]:
    stmt = (
        select(WatchTimelineEvent)
        .where(WatchTimelineEvent.watch_id == watch_id)
        .order_by(WatchTimelineEvent.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# ── Sources endpoints ─────────────────────────────────────────────────────────

@router.post("/product-watches/{watch_id}/sources", response_model=WatchSourceRead,
             status_code=201, tags=["sources"])
async def add_source(
    watch_id: uuid.UUID,
    body: WatchSourceCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    watch = await _get_watch_or_404(watch_id, db)
    svc = SourceService(db)
    source = await svc.add_source(watch, body)
    background_tasks.add_task(svc.run_check, source.id)
    return source


@router.get("/sources/{source_id}", response_model=WatchSourceRead, tags=["sources"])
async def get_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    return await _get_source_or_404(source_id, db)


@router.patch("/sources/{source_id}", response_model=WatchSourceRead, tags=["sources"])
async def update_source(
    source_id: uuid.UUID,
    body: WatchSourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    source = await _get_source_or_404(source_id, db)
    svc = SourceService(db)
    return await svc.update_source(source, body)


@router.delete("/sources/{source_id}", status_code=204, response_model=None, tags=["sources"])
async def archive_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    source = await _get_source_or_404(source_id, db)
    svc = SourceService(db)
    await svc.archive_source(source)


@router.post("/sources/{source_id}/pause", response_model=WatchSourceRead, tags=["sources"])
async def pause_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    source = await _get_source_or_404(source_id, db)
    svc = SourceService(db)
    return await svc.pause_source(source)


@router.post("/sources/{source_id}/resume", response_model=WatchSourceRead, tags=["sources"])
async def resume_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    source = await _get_source_or_404(source_id, db)
    svc = SourceService(db)
    return await svc.resume_source(source)


@router.post("/sources/{source_id}/check", response_model=WatchSourceRead, tags=["sources"])
async def trigger_source_check(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchSource:
    source = await _get_source_or_404(source_id, db)
    svc = SourceService(db)
    background_tasks.add_task(svc.run_check, source_id)
    return source


@router.get("/sources/{source_id}/checks", response_model=SourceCheckList, tags=["sources"])
async def get_source_checks(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> SourceCheckList:
    count_stmt = select(func.count()).where(SourceCheck.source_id == source_id)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        select(SourceCheck)
        .where(SourceCheck.source_id == source_id)
        .order_by(SourceCheck.checked_at.desc())
        .offset(skip).limit(limit)
    )
    items = (await db.execute(stmt)).scalars().all()
    return SourceCheckList(items=list(items), total=total)


@router.get("/sources/{source_id}/price-events", response_model=list[SourcePriceEventRead], tags=["sources"])
async def get_source_price_events(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
) -> list[SourcePriceEvent]:
    stmt = (
        select(SourcePriceEvent)
        .where(SourcePriceEvent.source_id == source_id)
        .order_by(SourcePriceEvent.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.post("/sources/{source_id}/diagnose", tags=["sources"])
async def diagnose_source(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Trigger Ollama parser-analyse for denne source i baggrunden."""
    source = await _get_source_or_404(source_id, db)
    background_tasks.add_task(_run_ollama_diagnose, source_id, str(source.url))
    return {"status": "queued", "source_id": str(source_id)}


async def _run_ollama_diagnose(source_id: uuid.UUID, url: str) -> None:
    """Kør Ollama parser-analyse for source i baggrunden (henter seneste fejl-check)."""
    from app.database import AsyncSessionLocal
    from app.services.ollama_service import ollama_service

    async with AsyncSessionLocal() as db:
        stmt = (
            select(SourceCheck)
            .where(SourceCheck.source_id == source_id, SourceCheck.success == False)
            .order_by(SourceCheck.checked_at.desc())
            .limit(1)
        )
        last_fail = (await db.execute(stmt)).scalar_one_or_none()
        if not last_fail:
            return

        diagnostic = last_fail.raw_diagnostic or {}
        html_snippet = diagnostic.get("html_snippet", "")
        if not html_snippet:
            return

        await ollama_service.analyze_parser(
            db=db,
            url=url,
            html_snippet=html_snippet,
            html_title=diagnostic.get("html_title", ""),
            status_code=last_fail.status_code or 0,
            failed_extractors=[],
            source_id=str(source_id),
        )
