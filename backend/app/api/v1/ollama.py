"""
API v1 — Ollama integration endpoints
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.v2 import OllamaAnalyzeRequest, OllamaConfigPatch, OllamaNormalizeRequest, OllamaStatusResponse
from app.services.ollama_service import ollama_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/status", response_model=OllamaStatusResponse)
async def ollama_status() -> OllamaStatusResponse:
    """Ping Ollama og returner tilgængelighed og tilgængelige modeller."""
    available = settings.ollama_enabled and await ollama_service.is_available()
    models = await ollama_service.list_models() if available else []
    return OllamaStatusResponse(
        available=available,
        enabled=settings.ollama_enabled,
        models=models,
        host=settings.ollama_host,
        parser_model=settings.ollama_parser_model,
        normalize_model=settings.ollama_normalize_model,
        embed_model=settings.ollama_embed_model,
    )


@router.patch("/config")
async def update_ollama_config(body: OllamaConfigPatch) -> OllamaStatusResponse:
    """Opdatér Ollama-config i runtime (gemmes ikke til disk — sæt env-vars for persistens)."""
    if body.enabled is not None:
        settings.ollama_enabled = body.enabled
    if body.host is not None:
        settings.ollama_host = body.host
        await ollama_service.close()   # tving ny klient med opdateret host
    if body.parser_model is not None:
        settings.ollama_parser_model = body.parser_model
    if body.normalize_model is not None:
        settings.ollama_normalize_model = body.normalize_model
    if body.embed_model is not None:
        settings.ollama_embed_model = body.embed_model
    # Return updated status
    available = settings.ollama_enabled and await ollama_service.is_available()
    models = await ollama_service.list_models() if available else []
    return OllamaStatusResponse(
        available=available,
        enabled=settings.ollama_enabled,
        models=models,
        host=settings.ollama_host,
        parser_model=settings.ollama_parser_model,
        normalize_model=settings.ollama_normalize_model,
        embed_model=settings.ollama_embed_model,
    )


@router.post("/analyze-parser")
async def analyze_parser(
    body: OllamaAnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Kør Ollama parser-analyse direkte (til test og debugging)."""
    advice = await ollama_service.analyze_parser(
        db=db,
        url=body.url,
        html_snippet=body.html_snippet,
        html_title=body.html_title,
        status_code=body.status_code,
        failed_extractors=body.failed_extractors,
    )
    if advice is None:
        return {"error": "Ollama ikke tilgængelig eller svarede ikke"}
    return {
        "page_type": advice.page_type,
        "price_selector": advice.price_selector,
        "stock_selector": advice.stock_selector,
        "requires_js": advice.requires_js,
        "likely_bot_protection": advice.likely_bot_protection,
        "reasoning": advice.reasoning,
        "recommended_action": advice.recommended_action,
        "confidence": advice.confidence,
    }


@router.post("/normalize-product")
async def normalize_product(
    body: OllamaNormalizeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Normalisér produkttitler via Ollama."""
    result = await ollama_service.normalize_product(db=db, titles=body.titles)
    if result is None:
        return {"error": "Ollama ikke tilgængelig eller svarede ikke"}
    return {
        "brand": result.brand,
        "model": result.model,
        "variant": result.variant,
        "mpn": result.mpn,
        "normalized_key": result.normalized_key,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }
