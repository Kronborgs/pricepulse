from __future__ import annotations

import re
from dataclasses import dataclass

import structlog
from bs4 import BeautifulSoup

from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

# Regex til at rense priser i HTML-tekst
PRICE_CLEAN_RE = re.compile(r"[^\d,.\s]")
PRICE_NUMBER_RE = re.compile(r"[\d.,]+")


@dataclass
class SelectorConfig:
    price_selector: str
    title_selector: str | None = None
    stock_selector: str | None = None
    image_selector: str | None = None
    price_attr: str | None = None        # Attribut frem for text (fx data-price)
    stock_in_text: str | None = None     # Tekst der indikerer "på lager"
    stock_out_text: str | None = None    # Tekst der indikerer "ikke på lager"


class CssSelectorParser(PriceParser):
    """
    Generisk konfigurerbar CSS-selector parser.
    Bruges til watches med bruger-definerede selectors,
    eller som fallback for kendte shops.
    """

    parser_name = "css_selector"

    def __init__(self, config: SelectorConfig) -> None:
        self.config = config

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        price = self._extract_price(soup)
        if price is None:
            return ParseResult(
                error=f"CSS-selector '{self.config.price_selector}' fandt ingen pris",
                parser_used=self.parser_name,
            )

        title = self._extract_text(soup, self.config.title_selector) if self.config.title_selector else None
        stock = self._extract_stock(soup)
        image = self._extract_image(soup)

        return ParseResult(
            title=title,
            price=price,
            currency="DKK",
            stock_status=stock,
            image_url=image,
            parser_used=self.parser_name,
        )

    def _extract_price(self, soup: BeautifulSoup) -> float | None:
        el = soup.select_one(self.config.price_selector)
        if not el:
            return None

        if self.config.price_attr:
            raw = el.get(self.config.price_attr, "")
        else:
            raw = el.get_text(strip=True)

        return self._parse_price(raw)

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str | None:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    def _extract_stock(self, soup: BeautifulSoup) -> str | None:
        if not self.config.stock_selector:
            return None
        el = soup.select_one(self.config.stock_selector)
        if not el:
            return None
        text = el.get_text(strip=True).lower()
        if self.config.stock_in_text and self.config.stock_in_text.lower() in text:
            return "in_stock"
        if self.config.stock_out_text and self.config.stock_out_text.lower() in text:
            return "out_of_stock"
        return text[:100]

    def _extract_image(self, soup: BeautifulSoup) -> str | None:
        if not self.config.image_selector:
            return None
        el = soup.select_one(self.config.image_selector)
        if not el:
            return None
        return el.get("src") or el.get("data-src")

    @staticmethod
    def _parse_price(raw: str) -> float | None:
        if not raw:
            return None
        cleaned = PRICE_CLEAN_RE.sub("", raw).strip()
        match = PRICE_NUMBER_RE.search(cleaned)
        if not match:
            return None
        num_str = match.group()
        # Dansk format: 1.299,00 → 1299.00
        if "," in num_str and "." in num_str:
            num_str = num_str.replace(".", "").replace(",", ".")
        elif "," in num_str:
            num_str = num_str.replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return None
