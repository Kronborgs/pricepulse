from __future__ import annotations

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

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    logger.info("PricePulse starting up", environment=settings.environment)

    # Opret tabeller hvis de ikke eksisterer (migrations håndterer dette i prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start APScheduler
    await start_scheduler()

    logger.info("PricePulse ready")
    yield

    # Shutdown
    logger.info("PricePulse shutting down")
    await stop_scheduler()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PricePulse API",
        description="Self-hosted prisovervågning til danske webshops",
        version="1.0.0",
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
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
