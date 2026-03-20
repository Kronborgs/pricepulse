from __future__ import annotations

import structlog

from app.scraper.providers.base import FetchOptions, FetchProvider, FetchResult

logger = structlog.get_logger()


class PlaywrightProvider(FetchProvider):
    """
    Browser-baseret provider via Playwright (Chromium headless).
    Bruges til sider der kræver JavaScript-rendering eller har bot-detection.
    Kræver at Playwright er installeret: playwright install chromium
    """

    provider_name = "playwright"

    async def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        opts = options or FetchOptions()

        try:
            from playwright.async_api import async_playwright, TimeoutError as PWTimeout
        except ImportError:
            return FetchResult(
                provider=self.provider_name,
                error="Playwright er ikke installeret. Sæt PLAYWRIGHT_ENABLED=true og genbyg containeren.",
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    locale="da-DK",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                # Bloker unødvendige ressourcer for hastighed
                await page.route(
                    "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
                    lambda route: route.abort(),
                )

                try:
                    await page.goto(
                        url,
                        wait_until="networkidle" if opts.wait_for_networkidle else "domcontentloaded",
                        timeout=opts.timeout * 1000,
                    )

                    if opts.wait_for_selector:
                        await page.wait_for_selector(
                            opts.wait_for_selector, timeout=10000
                        )

                    content = await page.content()
                    final_url = page.url

                except PWTimeout:
                    content = await page.content()
                    final_url = page.url
                    logger.warning("Playwright timeout — bruger hvad vi har", url=url)

                await browser.close()

                return FetchResult(
                    content=content,
                    status_code=200,
                    final_url=final_url,
                    provider=self.provider_name,
                )

        except Exception as e:
            logger.error("Playwright fejl", url=url, error=str(e))
            return FetchResult(
                provider=self.provider_name,
                error=f"Browser fejl: {e}",
            )
