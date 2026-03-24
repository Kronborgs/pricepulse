from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse

import structlog

from app.config import settings
from app.scraper.providers.base import ErrorType, FetchOptions, FetchProvider, FetchResult

logger = structlog.get_logger()

_domain_last_request: dict[str, float] = defaultdict(float)
_domain_lock: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _is_available() -> bool:
    try:
        import curl_cffi  # noqa: F401
        return True
    except ImportError:
        return False


class CurlCffiProvider(FetchProvider):
    """
    HTTP provider der impersonerer Chromes præcise TLS-fingerprint via curl_cffi.

    Omgår TLS-fingerprint (JA3/JA3N) baseret bot-beskyttelse ved at sende
    nøjagtigt de samme cipher suites, TLS extensions, HTTP/2 settings frames
    og GREASE-værdier som en rigtig Chrome-browser.

    Bruges automatisk som fallback når HTTP-provider får 403/bot_protection.
    Kan også sættes eksplicit som provider="curl_cffi".
    """

    provider_name = "curl_cffi"

    async def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        opts = options or FetchOptions()
        domain = urlparse(url).netloc

        if not _is_available():
            return FetchResult(
                provider=self.provider_name,
                error="curl_cffi er ikke installeret — genbyg containeren",
                error_type=ErrorType.transport_error,
            )

        # Per-domain rate limiting (delt state med http_provider)
        async with _domain_lock[domain]:
            elapsed = time.monotonic() - _domain_last_request[domain]
            if elapsed < settings.scraper_domain_delay:
                await asyncio.sleep(settings.scraper_domain_delay - elapsed)
            _domain_last_request[domain] = time.monotonic()

        start = time.monotonic()
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                resp = await session.get(
                    url,
                    impersonate="chrome124",
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Upgrade-Insecure-Requests": "1",
                    },
                    timeout=opts.timeout,
                    allow_redirects=True,
                )

            elapsed_ms = (time.monotonic() - start) * 1000
            content = resp.text

            if resp.status_code == 403:
                return FetchResult(
                    status_code=403,
                    provider=self.provider_name,
                    response_time_ms=elapsed_ms,
                    error="HTTP 403 Forbidden — siden blokerer (stærkt bot-filter)",
                    error_type=ErrorType.bot_protection,
                )
            if resp.status_code == 429:
                return FetchResult(
                    status_code=429,
                    provider=self.provider_name,
                    response_time_ms=elapsed_ms,
                    error="HTTP 429 Too Many Requests",
                    error_type=ErrorType.bot_protection,
                )
            if resp.status_code >= 400:
                return FetchResult(
                    status_code=resp.status_code,
                    provider=self.provider_name,
                    response_time_ms=elapsed_ms,
                    error=f"HTTP {resp.status_code}",
                    error_type=ErrorType.http_error,
                )

            return FetchResult(
                content=content,
                status_code=resp.status_code,
                final_url=str(resp.url),
                provider=self.provider_name,
                response_time_ms=elapsed_ms,
                html_length=len(content),
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning("curl_cffi fejl", url=url, error=str(exc))
            return FetchResult(
                provider=self.provider_name,
                response_time_ms=elapsed_ms,
                error=f"curl_cffi fejl: {exc}",
                error_type=ErrorType.transport_error,
            )
