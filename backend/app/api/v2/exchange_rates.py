"""
GET /exchange-rates  — returnerer daglige DKK-kurser fra Danmarks Nationalbank.
Ingen autentificering krævet (public data).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.services.exchange_rate_service import get_dkk_rates

router = APIRouter()


@router.get("/exchange-rates")
async def exchange_rates() -> dict:
    rates = await get_dkk_rates()
    return {
        "base": "DKK",
        "rates": rates,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
