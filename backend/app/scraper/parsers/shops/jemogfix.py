from __future__ import annotations

import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

# Regex til dansk pris-format i tekst: 49,50  / 1.299,00  / 49,-
_PRICE_RE = re.compile(
    r"(?<![,.\d])"            # ikke del af et tal
    r"(\d{1,3}(?:[.,]\d{3})*"  # tusind-separator
    r"(?:[,]\d{0,2}|-)?)"      # decimal med , eller ,- suffix
    r"(?=\s*(?:pr\.\s*stk|stk\.|,-|kr\.?|DKK|$))",
    re.IGNORECASE,
)


class JemogfixParser(PriceParser):
    """
    Parser til jemogfix.dk (Dynamicweb CMS).

    Strategier:
    1. CSS-selectors (Dynamicweb standard pris-elementer)
    2. Regex-scan af tekst nær køb-knap / produkt-blok
    """

    parser_name = "jemogfix"

    _css = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                # Dynamicweb standard
                ".product-price, "
                ".price-value, "
                ".unitPrice, "
                "[class*='UnitPrice'], "
                "[class*='unit-price'], "
                "[class*='ProductPrice'], "
                "[class*='product-price'], "
                # Generiske pris-elementer
                "[itemprop='price'], "
                ".price strong, "
                ".price, "
                "[class*='price'] strong"
            ),
            title_selector=(
                "h1[class*='product'], "
                "h1[itemprop='name'], "
                "h1"
            ),
            stock_selector=(
                "[class*='stock'], "
                "[class*='availability'], "
                "[itemprop='availability']"
            ),
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        # Strategi 1: CSS
        result = self._css.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
            return result

        # Strategi 2: Regex nær "læg i kurv" / produkt-sektion
        soup = BeautifulSoup(content, "lxml")
        price = self._regex_scan(soup)
        if price:
            h1 = soup.find("h1")
            return ParseResult(
                price=price,
                currency="DKK",
                title=h1.get_text(strip=True) if h1 else None,
                parser_used=self.parser_name,
            )

        return ParseResult(
            error="jemogfix: ingen pris fundet",
            parser_used=self.parser_name,
        )

    def _regex_scan(self, soup: BeautifulSoup) -> float | None:
        """
        Scan tekst-indhold af produkt-sektionen for priser.
        Søger primært i .product-info, .product-details, .add-to-cart-area.
        Falder tilbage til hele body.
        """
        candidates = (
            soup.select_one(
                ".product-info, .product-details, "
                ".add-to-cart, .buy-section, "
                ".productInfo, .product-summary, "
                "[class*='product'][class*='info'], "
                "[class*='buy']"
            )
            or soup.body
        )
        if not candidates:
            return None

        text = candidates.get_text(" ")
        for m in _PRICE_RE.finditer(text):
            p = _clean_price(m.group(1))
            if p and p > 1:
                return p
        return None
