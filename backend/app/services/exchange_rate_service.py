"""
Valutakurser — henter daglige kurser fra Danmarks Nationalbanks XML-API.
Kurser angives som DKK per 100 enheder i Nationalbankens feed, vi omregner til DKK per 1 enhed.
Caches i 24 timer (Nationalbanken opdaterer én gang dagligt ca. kl. 16).
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx
import structlog

logger = structlog.get_logger(__name__)

_CACHE: dict[str, float] | None = None
_CACHE_TS: datetime | None = None
_TTL = timedelta(hours=24)
_LOCK = asyncio.Lock()

# Nationalbankens XML-feed med dagens kurser (opdateres dagligt ~16:00)
_API_URL = "https://www.nationalbanken.dk/api/currencyratesxml?lang=da"

# Statisk fallback hvis API er nede
_FALLBACK: dict[str, float] = {
    "DKK": 1.0,
    "EUR": 7.46,
    "USD": 6.93,
    "GBP": 8.61,
    "SEK": 0.69,
    "NOK": 0.67,
    "CHF": 8.13,
    "JPY": 0.047,
    "CAD": 5.06,
    "AUD": 4.48,
}


def _parse_nationalbanken_xml(content: str) -> dict[str, float]:
    """
    Parser Nationalbankens XML-format.
    Kurser angives som DKK per 100 enheder udenlandsk valuta.
    Vi dividerer med 100 for at få DKK per 1 enhed.
    """
    root = ET.fromstring(content)
    rates: dict[str, float] = {"DKK": 1.0}

    for daily in root.iter("dailyrates"):
        for currency in daily.iter("currency"):
            code = currency.get("code", "").upper()
            raw = currency.get("rate", "").replace(",", ".")
            if code and raw:
                try:
                    rates[code] = round(float(raw) / 100, 6)
                except ValueError:
                    pass
        break  # kun første (seneste) dag

    return rates


async def get_dkk_rates() -> dict[str, float]:
    """
    Returnerer en dict med DKK-prisen for 1 enhed af hvert valuta.
    Eksempel: {"EUR": 7.4726, "USD": 6.44, "SEK": 0.6863, "DKK": 1.0, ...}
    Kilde: Danmarks Nationalbank — opdateres dagligt.
    """
    global _CACHE, _CACHE_TS

    now = datetime.now(timezone.utc)
    if _CACHE is not None and _CACHE_TS is not None and (now - _CACHE_TS) < _TTL:
        return _CACHE

    async with _LOCK:
        # Double-check inside lock
        now = datetime.now(timezone.utc)
        if _CACHE is not None and _CACHE_TS is not None and (now - _CACHE_TS) < _TTL:
            return _CACHE

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(_API_URL)
                resp.raise_for_status()

            rates = _parse_nationalbanken_xml(resp.text)

            _CACHE = rates
            _CACHE_TS = now
            logger.info(
                "exchange_rates.updated",
                source="nationalbanken",
                currencies=len(rates),
                eur_dkk=rates.get("EUR"),
            )
            return rates

        except Exception as exc:
            logger.warning("exchange_rates.fetch_failed", error=str(exc))
            if _CACHE is not None:
                return _CACHE
            return _FALLBACK.copy()
