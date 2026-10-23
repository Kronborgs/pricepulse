# Legacy v1 models
from app.database import Base

# AI Jobs
from app.models.ai_job import AIJob
from app.models.auth_token import AuthToken
from app.models.base import TimestampMixin
from app.models.email_preference import EmailPreference
from app.models.email_queue import EmailQueue
from app.models.llm_analysis_result import LlmAnalysisResult
from app.models.notification_rule import NotificationRule
from app.models.price_event import PriceEvent
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.product_snapshot import ProductSnapshot

# v2 models
from app.models.product_watch import ProductWatch

# Scraper reports
from app.models.scraper_report import ScraperReport
from app.models.shop import Shop

# Email / SMTP
from app.models.smtp_settings import SMTPSettings
from app.models.source_check import SourceCheck
from app.models.source_price_event import SourcePriceEvent

# Auth + Users
from app.models.user import User
from app.models.watch import Watch
from app.models.watch_source import WatchSource
from app.models.watch_timeline_event import WatchTimelineEvent

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
    "NotificationRule",
    # scraper reports
    "ScraperReport",
]
