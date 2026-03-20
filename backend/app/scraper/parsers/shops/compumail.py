from __future__ import annotations

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser


class CompumailParser(PriceParser):
    """
    Parser til compumail.dk.
    Forsøger JSON-LD først (understøttes), derefter CSS selectors.
    """

    parser_name = "compumail"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".price-box .price, .product-price .price, [data-price-amount]",
            title_selector="h1.page-title, .product-info-main h1",
            stock_selector=".stock.available, .availability",
            image_selector=".gallery-image.loaded, .product-img-box img",
            price_attr="data-price-amount",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result
