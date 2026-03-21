from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings
from app.scraper.providers.base import ErrorType, FetchOptions, FetchProvider, FetchResult

logger = structlog.get_logger()

# Globalt in-memory rate-limit state (domain → last request timestamp)
_domain_last_request: dict[str, float] = defaultdict(float)
_domain_lock: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

_SHARED_HEADERS = {
    "User-Agent": settings.scraper_user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}


class HttpProvider(FetchProvider):
    """
    Async HTTP provider baseret på httpx.
    Understøtter HTTP/2 med automatisk HTTP/1.1-fallback ved stream reset,
    connection pooling, og per-domain rate limiting.
    """

    provider_name = "http"

    def __init__(self) -> None:
        self._http2_client: httpx.AsyncClient | None = None
        self._http1_client: httpx.AsyncClient | None = None

    def _make_client(self, http2: bool) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            http2=http2,
            follow_redirects=True,
            timeout=30.0,
            headers=_SHARED_HEADERS,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    @property
    def http2_client(self) -> httpx.AsyncClient:
        if self._http2_client is None or self._http2_client.is_closed:
            self._http2_client = self._make_client(http2=True)
        return self._http2_client

    @property
    def http1_client(self) -> httpx.AsyncClient:
        if self._http1_client is None or self._http1_client.is_closed:
            self._http1_client = self._make_client(http2=False)
        return self._http1_client

    async def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        opts = options or FetchOptions()
        domain = urlparse(url).netloc

        # Per-domain rate limiting
        async with _domain_lock[domain]:
            elapsed = time.monotonic() - _domain_last_request[domain]
            if elapsed < settings.scraper_domain_delay:
                await asyncio.sleep(settings.scraper_domain_delay - elapsed)
            _domain_last_request[domain] = time.monotonic()

        return await self._fetch_with_fallback(url, opts, use_http2=True)

    async def _fetch_with_fallback(
        self, url: str, opts: FetchOptions, use_http2: bool
    ) -> FetchResult:
        """
        Forsøger at hente URL — ved HTTP/2 stream reset skiftes automatisk til HTTP/1.1.
        Derefter op til 2 genforsøg ved kortvarige netværksfejl.
        """
        client = self.http2_client if use_http2 else self.http1_client
        start = time.monotonic()

        for attempt in range(3):
            try:
                resp = await client.get(
                    url,
                    headers=opts.extra_headers or {},
                    timeout=opts.timeout,
                )
                elapsed_ms = (time.monotonic() - start) * 1000
                content = resp.text
                html_length = len(content)

                if resp.status_code == 403:
                    return FetchResult(
                        status_code=403,
                        provider=self.provider_name,
                        response_time_ms=elapsed_ms,
                        error="HTTP 403 Forbidden — siden blokerer scraping (muligt bot-filter)",
                        error_type=ErrorType.bot_protection,
                    )
                if resp.status_code == 429:
                    return FetchResult(
                        status_code=429,
                        provider=self.provider_name,
                        response_time_ms=elapsed_ms,
                        error="HTTP 429 Too Many Requests — rate limited",
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
                    html_length=html_length,
                )

            except httpx.RemoteProtocolError as exc:
                # HTTP/2 stream resets (PROTOCOL_ERROR / CANCEL) → retry with HTTP/1.1
                if use_http2:
                    logger.info(
                        "HTTP/2 stream reset — prøver med HTTP/1.1",
                        url=url,
                        error=str(exc),
                    )
                    return await self._fetch_with_fallback(url, opts, use_http2=False)
                # On HTTP/1.1 a RemoteProtocolError is a real failure
                return FetchResult(
                    provider=self.provider_name,
                    response_time_ms=(time.monotonic() - start) * 1000,
                    error=f"Protokolfejl: {exc}",
                    error_type=ErrorType.transport_error,
                )

            except httpx.TimeoutException:
                elapsed_ms = (time.monotonic() - start) * 1000
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return FetchResult(
                    provider=self.provider_name,
                    response_time_ms=elapsed_ms,
                    error="Request timeout",
                    error_type=ErrorType.timeout,
                )

            except httpx.TransportError as exc:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return FetchResult(
                    provider=self.provider_name,
                    response_time_ms=(time.monotonic() - start) * 1000,
                    error=f"Netværksfejl: {exc}",
                    error_type=ErrorType.transport_error,
                )

        # Fallback — should not be reached
        return FetchResult(
            provider=self.provider_name,
            error="Ukendt fejl",
            error_type=ErrorType.transport_error,
        )

    async def close(self) -> None:
        for client in (self._http2_client, self._http1_client):
            if client and not client.is_closed:
                await client.aclose()
