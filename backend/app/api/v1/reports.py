"""
Scraper-rapporter — brugere kan rapportere fejl på en Data Webscraper.
Admin/superuser kan se og håndtere rapporterne.
"""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role, SuperOrAdmin
from app.database import get_db
from app.models.scraper_report import ScraperReport
from app.models.user import User
from app.models.watch import Watch

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    watch_id: uuid.UUID
    comment: str | None = None


class ReporterOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None

    model_config = {"from_attributes": True}


class WatchOut(BaseModel):
    id: uuid.UUID
    url: str
    title: str | None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: uuid.UUID
    watch_id: uuid.UUID
    comment: str | None
    status: str
    created_at: str
    reporter: ReporterOut
    watch: WatchOut

    model_config = {"from_attributes": True}


class ReportList(BaseModel):
    items: List[ReportOut]
    total: int
    unread: int


# ── POST /reports — bruger indsender rapport ──────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReportOut)
async def create_report(
    body: ReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
):
    # Bekræft at watch eksisterer og brugeren har adgang
    watch = await db.get(Watch, body.watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch ikke fundet")

    # Ikke-privilegerede brugere kan kun rapportere egne watches
    if user.role not in ("admin", "superuser") and watch.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Ingen adgang til dette watch")

    report = ScraperReport(
        watch_id=body.watch_id,
        reporter_id=user.id,
        comment=body.comment,
        status="new",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Indlæs relationer eksplicit
    await db.refresh(report, ["watch", "reporter"])

    return _serialize(report)


# ── GET /reports — admin/superuser ser alle rapporter ─────────────────────────

@router.get("", response_model=ReportList)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(require_role("admin", "superuser")),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    report_status: str | None = Query(None, alias="status"),
):
    filters = []
    if report_status:
        filters.append(ScraperReport.status == report_status)

    total = (
        await db.execute(select(func.count(ScraperReport.id)).where(*filters))
    ).scalar_one()

    unread = (
        await db.execute(
            select(func.count(ScraperReport.id)).where(ScraperReport.status == "new")
        )
    ).scalar_one()

    rows = (
        await db.execute(
            select(ScraperReport)
            .where(*filters)
            .order_by(ScraperReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()

    return ReportList(
        items=[_serialize(r) for r in rows],
        total=total,
        unread=unread,
    )


# ── PATCH /reports/{id}/status — admin markerer rapport ──────────────────────

class StatusUpdate(BaseModel):
    status: str  # "read" | "resolved"


@router.patch("/{report_id}/status", response_model=ReportOut)
async def update_report_status(
    report_id: uuid.UUID,
    body: StatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(require_role("admin", "superuser")),
):
    if body.status not in ("new", "read", "resolved"):
        raise HTTPException(status_code=422, detail="Ugyldig status")

    report = await db.get(ScraperReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport ikke fundet")

    report.status = body.status
    await db.commit()
    await db.refresh(report, ["watch", "reporter"])
    return _serialize(report)


# ── DELETE /reports/{id} — admin sletter rapport ─────────────────────────────

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(require_role("admin", "superuser")),
):
    report = await db.get(ScraperReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport ikke fundet")
    await db.delete(report)
    await db.commit()


# ── GET /reports/unread-count — til dashboard badge ───────────────────────────

@router.get("/unread-count")
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(require_role("admin", "superuser")),
):
    count = (
        await db.execute(
            select(func.count(ScraperReport.id)).where(ScraperReport.status == "new")
        )
    ).scalar_one()
    return {"count": count}


# ── helpers ───────────────────────────────────────────────────────────────────

def _serialize(r: ScraperReport) -> ReportOut:
    return ReportOut(
        id=r.id,
        watch_id=r.watch_id,
        comment=r.comment,
        status=r.status,
        created_at=r.created_at.isoformat(),
        reporter=ReporterOut(
            id=r.reporter.id,
            email=r.reporter.email,
            display_name=r.reporter.display_name,
        ),
        watch=WatchOut(
            id=r.watch.id,
            url=r.watch.url,
            title=r.watch.title,
        ),
    )
