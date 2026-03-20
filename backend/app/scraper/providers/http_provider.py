from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.scraper.providers.base import FetchOptions, FetchProvider, FetchResult

logger = structlog.get_logger()

# Globalt in-memory rate-limit state (domain → last request timestamp)
_domain_last_request: dict[str, float] = defaultdict(float)
_domain_lock: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class HttpProvider(FetchProvider):
    """
    Async HTTP provider baseret på httpx.
    Understøtter HTTP/2, connection pooling, og per-domain rate limiting.
    """

    provider_name = "http"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                http2=True,
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": settings.scraper_user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                },
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        opts = options or FetchOptions()
        domain = urlparse(url).netloc

        # Per-domain rate limiting
        async with _domain_lock[domain]:
            elapsed = time.monotonic() - _domain_last_request[domain]
            if elapsed < settings.scraper_domain_delay:
                await asyncio.sleep(settings.scraper_domain_delay - elapsed)
            _domain_last_request[domain] = time.monotonic()

        return await self._fetch_with_retry(url, opts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_with_retry(self, url: str, opts: FetchOptions) -> FetchResult:
        try:
            headers = {**opts.extra_headers}
            resp = await self.client.get(url, headers=headers, timeout=opts.timeout)

            if resp.status_code == 403:
                return FetchResult(
                    status_code=403,
                    provider=self.provider_name,
                    error="HTTP 403 Forbidden — siden blokerer scraping (muligt bot-filter)",
                )
            if resp.status_code == 429:
                return FetchResult(
                    status_code=429,
                    provider=self.provider_name,
                    error="HTTP 429 Too Many Requests — rate limited",
                )
            if resp.status_code >= 400:
                return FetchResult(
                    status_code=resp.status_code,
                    provider=self.provider_name,
                    error=f"HTTP {resp.status_code}",
                )

            return FetchResult(
                content=resp.text,
                status_code=resp.status_code,
                final_url=str(resp.url),
                provider=self.provider_name,
            )

        except httpx.TimeoutException:
            return FetchResult(
                provider=self.provider_name,
                error="Request timeout",
            )
        except httpx.RequestError as e:
            return FetchResult(
                provider=self.provider_name,
                error=f"Network error: {e}",
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
