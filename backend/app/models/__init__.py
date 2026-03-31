# Legacy v1 models
from app.models.base import Base, TimestampMixin
from app.models.shop import Shop
from app.models.product import Product
from app.models.watch import Watch
from app.models.price_history import PriceHistory
from app.models.price_event import PriceEvent

# v2 models
from app.models.product_watch import ProductWatch
from app.models.watch_source import WatchSource
from app.models.source_check import SourceCheck
from app.models.source_price_event import SourcePriceEvent
from app.models.product_snapshot import ProductSnapshot
from app.models.watch_timeline_event import WatchTimelineEvent
from app.models.llm_analysis_result import LlmAnalysisResult

# Auth + Users
from app.models.user import User
from app.models.auth_token import AuthToken

# AI Jobs
from app.models.ai_job import AIJob

# Email / SMTP
from app.models.smtp_settings import SMTPSettings
from app.models.email_preference import EmailPreference
from app.models.email_queue import EmailQueue

# Scraper reports
from app.models.scraper_report import ScraperReport

__all__ = [
    # base
    "Base",
    "TimestampMixin",
    # legacy v1
    "Shop",
    "Product",
    "Watch",
    "PriceHistory",
    "PriceEvent",
    # v2
    "ProductWatch",
    "WatchSource",
    "SourceCheck",
    "SourcePriceEvent",
    "ProductSnapshot",
    "WatchTimelineEvent",
    "LlmAnalysisResult",
    # auth
    "User",
    "AuthToken",
    # ai
    "AIJob",
    # email
    "SMTPSettings",
    "EmailPreference",
    "EmailQueue",
    # scraper reports
    "ScraperReport",
]
