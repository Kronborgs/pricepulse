"""
Valutakurser — henter live EUR-baserede kurser fra Frankfurter API (ECB data).
Rates caches i 1 time i hukommelsen.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import structlog

logger = structlog.get_logger(__name__)

_CACHE: dict[str, object] | None = None
_CACHE_TS: datetime | None = None
_TTL = timedelta(hours=1)
_LOCK = asyncio.Lock()

_API_URL = "https://api.frankfurter.app/latest"


async def get_dkk_rates() -> dict[str, float]:
    """
    Returnerer en dict med DKK-prisen for 1 enhed af hvert valuta.
    Eksempel: {"EUR": 7.47, "USD": 6.59, "SEK": 0.69, "DKK": 1.0, ...}
    Cursen er baseret på ECB-data via Frankfurter API og opdateres hver time.
    """
    global _CACHE, _CACHE_TS

    now = datetime.now(timezone.utc)
    if _CACHE is not None and _CACHE_TS is not None and (now - _CACHE_TS) < _TTL:
        return _CACHE  # type: ignore[return-value]

    async with _LOCK:
        # Double-check inside lock
        now = datetime.now(timezone.utc)
        if _CACHE is not None and _CACHE_TS is not None and (now - _CACHE_TS) < _TTL:
            return _CACHE  # type: ignore[return-value]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(_API_URL)
                resp.raise_for_status()
                data = resp.json()

            # data["rates"] er EUR-baserede kurser: {"USD": 1.08, "DKK": 7.47, ...}
            eur_rates: dict[str, float] = data["rates"]
            dkk_per_eur: float = eur_rates.get("DKK", 7.46)

            rates: dict[str, float] = {"DKK": 1.0, "EUR": dkk_per_eur}
            for code, rate_from_eur in eur_rates.items():
                if code != "DKK" and rate_from_eur and rate_from_eur > 0:
                    rates[code] = round(dkk_per_eur / rate_from_eur, 6)

            _CACHE = rates
            _CACHE_TS = now
            logger.info("exchange_rates.updated", currencies=len(rates), eur_dkk=dkk_per_eur)
            return rates

        except Exception as exc:
            logger.warning("exchange_rates.fetch_failed", error=str(exc))
            # Returnér cached data hvis tilgængeligt, ellers fallback
            if _CACHE is not None:
                return _CACHE  # type: ignore[return-value]
            return {"DKK": 1.0, "EUR": 7.46}  # statisk fallback
