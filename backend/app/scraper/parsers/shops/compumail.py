from __future__ import annotations

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser


class CompumailParser(PriceParser):
    """
    Parser til compumail.dk.
    Forsøger JSON-LD først (understøttes), derefter CSS selectors.
    """

    parser_name = "compumail"

    # compumail.dk bruger sin egen platform (ikke Magento).
    # Pris:  <span class="price" data-price="2422">2\xa0422,00</span>
    # Titel: <h1 itemprop="name">...</h1>
    # Lager: JS-loaded — ikke tilgængeligt i server-side HTML
    _css_parser = CssSelectorParser(
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

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result
