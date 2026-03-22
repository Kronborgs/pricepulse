"""
AIJobService — opretter og opdaterer ai_jobs rækker.

Bruges af OllamaQueue og API-endpoints til at logge alle Ollama-kald.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job import AIJob

logger = structlog.get_logger(__name__)


class AIJobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        job_type: str,
        source_id: uuid.UUID | None = None,
        watch_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        triggered_by: uuid.UUID | None = None,
        prompt_summary: str | None = None,
        input_data: dict | None = None,
        model_used: str | None = None,
    ) -> AIJob:
        """Opret nyt AI-job med status='queued'."""
        job = AIJob(
            job_type=job_type,
            status="queued",
            model_used=model_used,
            source_id=source_id,
            watch_id=watch_id,
            product_id=product_id,
            triggered_by=triggered_by,
            prompt_summary=prompt_summary,
            input_data=input_data,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info(
            "ai_job_created",
            job_id=str(job.id),
            job_type=job_type,
            source_id=str(source_id) if source_id else None,
        )
        return job

    async def mark_processing(self, job_id: uuid.UUID, model_used: str) -> None:
        job = await self.db.get(AIJob, job_id)
        if job:
            job.status = "processing"
            job.model_used = model_used
            job.started_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def mark_completed(
        self,
        job_id: uuid.UUID,
        output_data: dict | None = None,
        summary: str | None = None,
        prompt_tokens: int | None = None,
        response_tokens: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        job = await self.db.get(AIJob, job_id)
        if job:
            job.status = "completed"
            job.output_data = output_data
            job.summary = summary
            job.prompt_tokens = prompt_tokens
            job.response_tokens = response_tokens
            job.duration_ms = duration_ms
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def mark_failed(self, job_id: uuid.UUID, error: str) -> None:
        job = await self.db.get(AIJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = error
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        source_id: uuid.UUID | None = None,
        watch_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AIJob], int]:
        from sqlalchemy import func
        query = select(AIJob)
        count_query = select(func.count(AIJob.id))

        if job_type:
            query = query.where(AIJob.job_type == job_type)
            count_query = count_query.where(AIJob.job_type == job_type)
        if status:
            query = query.where(AIJob.status == status)
            count_query = count_query.where(AIJob.status == status)
        if source_id:
            query = query.where(AIJob.source_id == source_id)
            count_query = count_query.where(AIJob.source_id == source_id)
        if watch_id:
            query = query.where(AIJob.watch_id == watch_id)
            count_query = count_query.where(AIJob.watch_id == watch_id)

        query = query.order_by(AIJob.queued_at.desc()).offset(skip).limit(limit)
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get(self, job_id: uuid.UUID) -> AIJob | None:
        return await self.db.get(AIJob, job_id)

    async def cancel(self, job_id: uuid.UUID) -> bool:
        job = await self.db.get(AIJob, job_id)
        if not job or job.status != "queued":
            return False
        job.status = "cancelled"
        await self.db.commit()
        return True
