"""
AI Jobs API — log og administration af Ollama-kald.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, SuperOrAdmin, CurrentUser
from app.database import get_db
from app.services.ai_job_service import AIJobService

logger = structlog.get_logger(__name__)
router = APIRouter()


class AIJobRead(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    model_used: str | None
    source_id: uuid.UUID | None
    watch_id: uuid.UUID | None
    product_id: uuid.UUID | None
    triggered_by: uuid.UUID | None
    prompt_summary: str | None
    summary: str | None
    error_message: str | None
    prompt_tokens: int | None
    response_tokens: int | None
    duration_ms: int | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AIJobDetail(AIJobRead):
    input_data: dict | None
    output_data: dict | None


@router.get("/jobs")
async def list_ai_jobs(
    job_type: str | None = None,
    status: str | None = None,
    source_id: uuid.UUID | None = None,
    watch_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    svc = AIJobService(db)
    jobs, total = await svc.list_jobs(
        job_type=job_type,
        status=status,
        source_id=source_id,
        watch_id=watch_id,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [AIJobRead.model_validate(j) for j in jobs],
        "total": total,
    }


@router.get("/jobs/{job_id}", response_model=AIJobDetail)
async def get_ai_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> AIJobDetail:
    svc = AIJobService(db)
    job = await svc.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ikke fundet")
    return AIJobDetail.model_validate(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_ai_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    svc = AIJobService(db)
    ok = await svc.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Job kan ikke annulleres (ikke i 'queued' status)")
    return {"ok": True}


@router.post("/diagnose/source/{source_id}")
async def trigger_source_diagnose(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: SuperOrAdmin = None,
) -> dict:
    """Trigger manuel parser-diagnose for en WatchSource."""
    from sqlalchemy import select
    from app.models.watch_source import WatchSource
    from app.services.ollama_queue import OllamaJob, enqueue

    source = await db.scalar(select(WatchSource).where(WatchSource.id == source_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source ikke fundet")

    if not source.last_diagnostic:
        raise HTTPException(
            status_code=400,
            detail="Ingen diagnostik tilgængelig — kør et check først"
        )

    html = source.last_diagnostic.get("html_snippet", "")
    enqueue(OllamaJob(
        entity_type="source",
        entity_id=source.id,
        url=source.url,
        html_snippet=html,
        extractors_tried=[],
        status_code=source.last_diagnostic.get("status_code", 200),
        scraper_config=source.scraper_config,
        diagnostic=source.last_diagnostic,
        previous_status=source.status,
    ))
    return {"ok": True, "message": "Diagnose lagt i kø"}


@router.get("/stats")
async def ai_stats(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Statistik over AI-job forbrug."""
    from sqlalchemy import func, select
    from app.models.ai_job import AIJob

    rows = await db.execute(
        select(
            AIJob.job_type,
            AIJob.status,
            func.count(AIJob.id).label("count"),
            func.sum(AIJob.prompt_tokens).label("prompt_tokens"),
            func.sum(AIJob.response_tokens).label("response_tokens"),
        ).group_by(AIJob.job_type, AIJob.status)
    )
    data = rows.all()
    return {
        "by_type_status": [
            {
                "job_type": r.job_type,
                "status": r.status,
                "count": r.count,
                "prompt_tokens": r.prompt_tokens or 0,
                "response_tokens": r.response_tokens or 0,
            }
            for r in data
        ]
    }
