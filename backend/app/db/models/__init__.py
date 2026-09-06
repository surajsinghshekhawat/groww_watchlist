"""Import all models so Alembic and metadata see them."""

from app.db.models.event_feedback import EventFeedback, FeedbackLabel
from app.db.models.instrument import Exchange, Instrument, TradingCategory
from app.db.models.market_data import PricePoint
from app.db.models.market_event import (
    EventEvidence,
    EventStatus,
    EventType,
    MarketEvent,
    Severity,
)
from app.db.models.notification import Notification
from app.db.models.push_subscription import PushSubscription
from app.db.models.snapshot import WatchlistSnapshot
from app.db.models.user import Sensitivity, User
from app.db.models.watchlist import Watchlist, WatchlistItem

__all__ = [
    "User",
    "Sensitivity",
    "Instrument",
    "Exchange",
    "TradingCategory",
    "Watchlist",
    "WatchlistItem",
    "PricePoint",
    "MarketEvent",
    "EventEvidence",
    "EventType",
    "Severity",
    "EventStatus",
    "WatchlistSnapshot",
    "Notification",
    "PushSubscription",
    "EventFeedback",
    "FeedbackLabel",
]
