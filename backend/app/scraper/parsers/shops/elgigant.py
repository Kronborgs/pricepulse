from __future__ import annotations

import json
import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

_PRICE_RE = re.compile(r'"price"\s*:\s*(\d+(?:\.\d+)?)')
_TITLE_RE = re.compile(r'"name"\s*:\s*"([^"]+)"')


class ElgigantParser(PriceParser):
    """
    Parser til www.elgiganten.dk (Next.js / Elkjøp Nordic platform).

    Forsøger tre strategier:
    1. JSON-LD (håndteres af JsonLdParser — allerede prøvet)
    2. __NEXT_DATA__ embedded JSON blob i <script id="__NEXT_DATA__">
    3. CSS-selectors som fallback
    """

    parser_name = "elgigant"

    # CSS fallback — elgiganten bruger Next.js SSR med data-testid attributter
    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                "[data-testid='product-price-value'], "
                "[data-testid='price'], "
                ".product-price-now, "
                "span[class*='ProductPrice'], "
                "span[class*='price'][class*='now']"
            ),
            title_selector="h1",
            image_selector="img[class*='product'], img[alt][src*='elkjop']",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        # Strategy 1: __NEXT_DATA__ JSON blob
        result = self._parse_next_data(content)
        if result and result.success:
            return result

        # Strategy 2: CSS selectors
        css_result = self._css_parser.parse(content, url)
        if css_result.success:
            css_result.parser_used = self.parser_name
            return css_result

        return ParseResult(
            error="elgigant: ingen pris fundet via __NEXT_DATA__ eller CSS",
            parser_used=self.parser_name,
        )

    def _parse_next_data(self, content: str) -> ParseResult | None:
        """Udtræk pris fra Next.js __NEXT_DATA__ JSON blob."""
        soup = BeautifulSoup(content, "lxml")
        script = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
        if not script:
            return None

        raw = script.get_text(strip=False)
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

        # Traverse the Next.js props tree looking for product price
        # Common paths: props.pageProps.product / props.pageProps.initialData.product
        product = self._find_product(data)
        if not product:
            return None

        price = self._extract_price_from_product(product)
        if price is None:
            return None

        title = product.get("name") or product.get("title")
        image = self._extract_image(product)
        stock = self._extract_stock(product)

        return ParseResult(
            title=title,
            price=price,
            currency="DKK",
            stock_status=stock,
            image_url=image,
            parser_used=self.parser_name,
        )

    @staticmethod
    def _find_product(data: dict) -> dict | None:
        """Walk Next.js data tree looking for a product-like dict."""
        # Try common pageProps paths
        page_props = (
            data.get("props", {}).get("pageProps") or {}
        )
        for key in ("product", "productData", "item", "article"):
            candidate = page_props.get(key)
            if isinstance(candidate, dict):
                return candidate

        # Try nested initialData / data / pdp
        for wrapper_key in ("initialData", "data", "pdp", "productPage"):
            wrapper = page_props.get(wrapper_key)
            if isinstance(wrapper, dict):
                for key in ("product", "item", "article"):
                    candidate = wrapper.get(key)
                    if isinstance(candidate, dict):
                        return candidate

        return None

    @staticmethod
    def _extract_price_from_product(product: dict) -> float | None:
        """Extract numeric price from a product dict (many possible shapes)."""
        # Direct price fields
        for field in ("price", "finalPrice", "salePrice", "currentPrice"):
            val = product.get(field)
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val)
                except ValueError:
                    pass

        # Nested prices object: {"current": 1099, "original": 1299}
        prices = product.get("prices") or product.get("pricing")
        if isinstance(prices, dict):
            for key in ("current", "sale", "final", "now"):
                val = prices.get(key)
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, dict):
                    for inner_key in ("price", "amount", "value"):
                        inner = val.get(inner_key)
                        if isinstance(inner, (int, float)):
                            return float(inner)

        return None

    @staticmethod
    def _extract_image(product: dict) -> str | None:
        img = product.get("image") or product.get("imageUrl") or product.get("primaryImage")
        if isinstance(img, str):
            return img
        if isinstance(img, dict):
            return img.get("url") or img.get("src")
        return None

    @staticmethod
    def _extract_stock(product: dict) -> str | None:
        for key in ("availability", "inStock", "stockStatus"):
            val = product.get(key)
            if val is True:
                return "in_stock"
            if val is False:
                return "out_of_stock"
            if isinstance(val, str):
                lower = val.lower()
                if any(s in lower for s in ("instock", "in_stock", "på lager", "available")):
                    return "in_stock"
                if any(s in lower for s in ("outofstock", "out_of_stock", "udsolgt")):
                    return "out_of_stock"
        return None
