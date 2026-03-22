from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.database import engine, Base
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.services.ollama_queue import process_queue_forever

logger = structlog.get_logger()

# Indsættes som build-arg PRICEPULSE_VERSION i Dockerfile
_VERSION = os.getenv("PRICEPULSE_VERSION", "dev")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    logger.info("PricePulse starting up", environment=settings.environment)

    # Opret tabeller hvis de ikke eksisterer (migrations håndterer dette i prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start APScheduler (tilføjer email-job her)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    await start_scheduler()
    _register_email_job()

    # Start sekventiel Ollama-kø-worker
    _ollama_worker = asyncio.create_task(process_queue_forever())

    logger.info("PricePulse ready")
    yield

    # Shutdown
    logger.info("PricePulse shutting down")
    _ollama_worker.cancel()
    await stop_scheduler()
    await engine.dispose()


def _register_email_job() -> None:
    """Registrér APScheduler-job til email-udsendelse hvert 5. minut."""
    try:
        from app.scheduler.jobs import scheduler
        from app.services.smtp_service import smtp_service

        async def _send_emails():
            await smtp_service.send_pending_emails()

        # Undgå dubletter ved hot-reload
        if not scheduler.get_job("send_pending_emails"):
            scheduler.add_job(
                _send_emails,
                trigger="interval",
                minutes=5,
                id="send_pending_emails",
                replace_existing=True,
            )
    except Exception as exc:
        logger.warning("email_job_registration_fejl", error=str(exc))


def create_app() -> FastAPI:
    app = FastAPI(
        title="PricePulse API",
        description="Self-hosted prisovervågning til danske webshops",
        version=_VERSION,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok", "version": _VERSION}

    return app


app = create_app()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PricePulse API",
        description="Self-hosted prisovervågning til danske webshops",
        version=_VERSION,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok", "version": _VERSION}

    return app


app = create_app()
