from __future__ import annotations

import structlog

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


class ElgigantParser(PriceParser):
    """
    Parser til www.elgiganten.dk (Elkjøp Nordic platform).

    Siden er en hybrid SSR/CSR Next.js-app. Prisen er tilgængelig i
    server-renderet HTML som en ``data-primary-price``-attribut på
    buy-box-elementet. Ingen __NEXT_DATA__ blob er indlejret, og JSON-LD
    bruger priceSpecification (ex-moms) frem for et direkte ``price``-felt.

    Strategi 1: specifik buy-box selector                      (mest præcis)
    Strategi 2: første [data-primary-price] på siden           (bredere fallback)
    """

    parser_name = "elgigant"

    # Strategi 1: Specifik buy-box — undgår tilbehørs-priser
    _strategy_buybox = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-cro='pdp-main-price-box'] [data-primary-price]",
            price_attr="data-primary-price",
            title_selector="h1",
            image_selector="img[data-nimg][alt][src*='dv_web']",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    # Strategi 2: Første data-primary-price-element på siden
    # (produkt-prisen optræder altid før tilbehørs-priser i DOM-rækkefølge)
    _strategy_any = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-primary-price]",
            price_attr="data-primary-price",
            title_selector="h1",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        for strategy in (self._strategy_buybox, self._strategy_any):
            result = strategy.parse(content, url)
            if result.success:
                result.parser_used = self.parser_name
                return result

        return ParseResult(
            error="elgigant: ingen pris fundet via data-primary-price",
            parser_used=self.parser_name,
        )
