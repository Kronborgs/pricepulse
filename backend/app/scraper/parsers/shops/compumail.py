from __future__ import annotations

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser


class CompumailParser(PriceParser):
    """
    Parser til compumail.dk.
    Forsøger JSON-LD først (understøttes), derefter CSS selectors.
    """

    parser_name = "compumail"

    # Strategi 1: Primær CSS — data-price attribut på span.price (inc-moms)
    # Struktur: <span class="price-novat"><span class="price" data-price="2422">
    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector="span.price[data-price]",
            title_selector="h1[itemprop='name']",
            stock_selector=None,
            image_selector=".product-lightbox-item.active img, .product-lightbox-item img",
            price_attr="data-price",
            stock_in_text="in stock",
            stock_out_text="out of stock",
        )
    )

    # Strategi 2: Bredere selector — enhver span med data-price
    _css_any_data_price = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-price]",
            price_attr="data-price",
            title_selector="h1[itemprop='name'], h1",
        )
    )

    # Strategi 3: Microdata fallback
    _css_microdata = CssSelectorParser(
        SelectorConfig(
            price_selector="[itemprop='price']",
            price_attr="content",
            title_selector="h1[itemprop='name'], h1",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        for strategy in (self._css_primary, self._css_any_data_price, self._css_microdata):
            result = strategy.parse(content, url)
            if result.success:
                result.parser_used = self.parser_name
                return result
        return ParseResult(
            error="compumail: ingen pris fundet",
            parser_used=self.parser_name,
        )

