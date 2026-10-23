"""
CpuPriceParser — ren Python/regex-baseret pris-udtrækker fra HTML.

Bruges som CPU-fallback når Ollama er offline eller parser fejler.
Strategi (kører i rækkefølge, returnerer ved første hit):
  A. JSON-LD / Schema.org microdata (data-attributter)
  B. Broad CSS-scan: klasser med "price" i navn → regexp-validering
  C. data-attributter direkte (data-price, data-product-price, etc.)
  D. Regex-pris i fri tekst med kr/DKK kontekst
  E. Open Graph price:price meta-tags

Ingen AI eller eksterne kald — alt kører lokalt på HTML'en.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()

# Regex der matcher danske/nordiske priser i fri tekst
_PRICE_RE = re.compile(
    r"""
    (?<!\d)
    (\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?)   # 1.299,00 / 1 299,00 / 12345
    |
    (\d{1,6})(?:,-)?                        # 949,- / 949
    (?=\s*(?:kr\.?|DKK|,-)\b)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# CSS-selectors der typisk indeholder pris-tekst
_PRICE_TEXT_SELECTORS = [
    # Schema.org microdata
    "[itemprop='price']",
    "[itemprop='offers'] [itemprop='price']",
    # WooCommerce
    ".woocommerce-Price-amount",
    ".price .amount",
    "bdi",
    # Generiske mønstre
    "[class*='price__amount']",
    "[class*='amount__price']",
    "[class*='product-price__value']",
    "[class*='price-value']",
    "[class*='PriceValue']",
    "[class*='PriceAmount']",
    "[class*='current-price']",
    "[class*='CurrentPrice']",
    "[class*='sale-price']",
    "[class*='final-price']",
    "[class*='ProductPrice']",
    # Magento
    ".price-wrapper .price",
    "[data-price-type='finalPrice'] .price",
    # Shopify
    ".product__price",
    ".price__regular",
    ".price__sale",
    # Sikker bred fallback
    "span[class*='price']",
    "div[class*='price'] span",
    "p[class*='price']",
]

# data-attributter der direkte indeholder prisen som tal
_PRICE_ATTR_SELECTORS = [
    ("[data-price]", "data-price"),
    ("[data-product-price]", "data-product-price"),
    ("[data-amount]", "data-amount"),
    ("[data-final-price]", "data-final-price"),
    ("[data-regular-price]", "data-regular-price"),
    ("[data-sale-price]", "data-sale-price"),
    ("[itemprop='price'][content]", "content"),
]

# Regex til at rense priser i HTML-tekst
_PRICE_CLEAN_RE = re.compile(r"[^\d,.\s]")
_PRICE_NUMBER_RE = re.compile(r"[\d.,]+")


@dataclass
class CpuParseResult:
    """Lignende ParseResult men uden async krav."""
    price: float | None
    title: str | None = None
    currency: str = "DKK"
    stock_status: str | None = None
    image_url: str | None = None
    parser_used: str = "cpu_parser"
    extractors_tried: list[str] | None = None


class CpuPriceParser:
    """
    CPU-baseret pris-udtrækker — ingen AI, ingen eksterne kald.
    
    Bruges som fallback når Ollama er offline eller parser fejler.
    Kører rent lokalt på HTML'en med regex og BeautifulSoup.
    """

    @staticmethod
    def parse(content: str, url: str = "") -> CpuParseResult | None:
        """
        Prøver at ekstrahere pris fra HTML via flere strategier.
        
        Returnerer CpuParseResult ved succes, None hvis ingen pris fundet.
        """
        if not content or len(content) < 100:
            return None

        soup = BeautifulSoup(content, "lxml")
        extractors_tried: list[str] = []

        # Strategi A: JSON-LD / Schema.org microdata
        result = CpuPriceParser._extract_from_jsonld(soup, content)
        if result:
            extractors_tried.append("json_ld")
            logger.debug("cpu_parser_json_ld", price=result)
            return CpuParseResult(
                price=result, title=None, currency="DKK",
                parser_used="cpu_parser/json_ld", extractors_tried=extractors_tried,
            )

        # Strategi B: data-attributter (data-price, etc.)
        result = CpuPriceParser._extract_from_attributes(soup)
        if result:
            extractors_tried.append("data_attributes")
            logger.debug("cpu_parser_data_attr", price=result)
            return CpuParseResult(
                price=result, title=None, currency="DKK",
                parser_used="cpu_parser/data_attr", extractors_tried=extractors_tried,
            )

        # Strategi C: CSS-scan for pris-elementer
        result = CpuPriceParser._extract_from_css_scan(soup)
        if result:
            extractors_tried.append("css_scan")
            logger.debug("cpu_parser_css_scan", price=result)
            return CpuParseResult(
                price=result, title=None, currency="DKK",
                parser_used="cpu_parser/css_scan", extractors_tried=extractors_tried,
            )

        # Strategi D: Regex i fri tekst (kun body)
        result = CpuPriceParser._extract_from_text(content, soup)
        if result:
            extractors_tried.append("text_regex")
            logger.debug("cpu_parser_text_regex", price=result)
            return CpuParseResult(
                price=result, title=None, currency="DKK",
                parser_used="cpu_parser/text_regex", extractors_tried=extractors_tried,
            )

        logger.debug("cpu_parser_ingen_pris", url=url)
        return None

    @staticmethod
    def _extract_from_jsonld(soup: BeautifulSoup, html: str) -> float | None:
        """Strategi A: JSON-LD / Schema.org microdata."""
        # JSON-LD scripts
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try: offers_json = __import__("json").loads(script.string)
            except Exception:
                continue

            def _search_json(obj: Any) -> float | None:
                if isinstance(obj, dict):
                    # Tjek singleOffer eller offer direkte
                    for key in ("price", "lowPrice", "highPrice"):
                        if key in obj and key in ("price", "lowPrice", "highPrice"):
                            val = obj[key]
                            if isinstance(val, (int, float)):
                                return float(val) if float(val) > 0 else None
                        elif key == "offers":
                            result = _search_json(obj[key])
                            if result:
                                return result
                    # Rekursivt søg i alle children
                    for val in obj.values():
                        result = _search_json(val)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = _search_json(item)
                        if result:
                            return result
                return None

            price = _search_json(offers_json)
            if price and price > 0:
                return price

        # Meta-tags (open graph price)
        for meta in soup.find_all("meta", property=re.compile(r"^(og|product):price")):
            content = meta.get("content", "")
            price = CpuPriceParser._parse_price(content)
            if price and price > 0:
                return price

        return None

    @staticmethod
    def _extract_from_attributes(soup: BeautifulSoup) -> float | None:
        """Strategi B: data-attributter."""
        for selector, attr in _PRICE_ATTR_SELECTORS:
            for el in soup.select(selector):
                val = el.get(attr, "")
                price = CpuPriceParser._parse_price(val)
                if price and price > 0:
                    return price
        return None

    @staticmethod
    def _extract_from_css_scan(soup: BeautifulSoup) -> float | None:
        """Strategi C: CSS-scan for pris-elementer."""
        for selector in _PRICE_TEXT_SELECTORS:
            for el in soup.select(selector):
                text = el.get_text(strip=True)
                price = CpuPriceParser._parse_price(text)
                if price and price > 0:
                    return price
        return None

    @staticmethod
    def _extract_from_text(html: str, soup: BeautifulSoup) -> float | None:
        """Strategi D: Regex i fri tekst (kun body)."""
        body = soup.find("body")
        if not body:
            # Fallback til hele HTML'en
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
        else:
            # Fjern script/style tags fra body
            text = body.get_text(" ", strip=True)

        # Find alle matcher
        matches = _PRICE_RE.findall(text)
        for match in matches:
            # match er en tuple af grupper
            price_str = match[0] or match[1]
            if price_str:
                price = CpuPriceParser._parse_price(price_str)
                if price and price > 0:
                    return price

        return None

    @staticmethod
    def _parse_price(raw: str) -> float | None:
        """Parse en pris-streng til float (understøtter dansk format)."""
        if not raw:
            return None
        cleaned = _PRICE_CLEAN_RE.sub("", raw).strip()
        match = _PRICE_NUMBER_RE.search(cleaned)
        if not match:
            return None
        num_str = match.group()
        # Dansk format: 1.299,00 → 1299.00
        if "," in num_str and "." in num_str:
            num_str = num_str.replace(".", "").replace(",", ".")
        elif "," in num_str:
            after_comma = num_str.rsplit(",", 1)[-1]
            if len(after_comma) == 3 and after_comma.isdigit():
                num_str = num_str.replace(",", "")
            else:
                num_str = num_str.replace(",", ".")
        elif "." in num_str:
            after_last_dot = num_str.rsplit(".", 1)[-1]
            if len(after_last_dot) == 3 and after_last_dot.isdigit():
                num_str = num_str.replace(".", "")
        try:
            val = float(num_str)
            return val if val > 0 else None
        except ValueError:
            return None
