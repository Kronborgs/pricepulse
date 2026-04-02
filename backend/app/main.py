from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import engine, Base
from app.limiter import limiter
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
    """Registrér APScheduler-jobs til email-udsendelse."""
    try:
        from app.scheduler.jobs import scheduler
        from app.services.smtp_service import smtp_service

        async def _send_emails():
            await smtp_service.send_pending_emails()

        async def _send_digests():
            await smtp_service.send_due_digests()

        # Undgå dubletter ved hot-reload
        if not scheduler.get_job("send_pending_emails"):
            scheduler.add_job(
                _send_emails,
                trigger="interval",
                minutes=5,
                id="send_pending_emails",
                replace_existing=True,
            )
        if not scheduler.get_job("send_digests"):
            scheduler.add_job(
                _send_digests,
                trigger="interval",
                minutes=30,
                id="send_digests",
                replace_existing=True,
            )
    except Exception as exc:
        logger.warning("email_job_registration_fejl", error=str(exc))


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Tilføjer standard sikkerhedsheadere til alle svar."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if settings.cookie_secure:
            # Kun meningsfuldt over HTTPS
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


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
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )

    # Sikkerhedsheadere
    app.add_middleware(_SecurityHeadersMiddleware)

    # Rate limiter state + handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok", "version": _VERSION}

    return app


app = create_app()
