from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FetchOptions:
    timeout: float = 30.0
    wait_for_selector: str | None = None    # Playwright: vent på element
    wait_for_networkidle: bool = True        # Playwright: vent på ro i netværk
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class FetchResult:
    content: str = ""
    status_code: int = 0
    final_url: str = ""
    provider: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code in range(200, 300)


@dataclass
class ParseResult:
    title: str | None = None
    price: float | None = None
    currency: str = "DKK"
    stock_status: str | None = None
    image_url: str | None = None
    ean: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    parser_used: str = ""
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.price is not None


class FetchProvider:
    """Base class for alle fetch providers."""

    provider_name: str = "base"

    async def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        raise NotImplementedError

    async def close(self) -> None:
        """Frigiv ressourcer (connections, browsers, etc.)."""


class PriceParser:
    """Base class for alle parsers."""

    parser_name: str = "base"

    def parse(self, content: str, url: str) -> ParseResult:
        raise NotImplementedError
