"""Provider factory from MARKET_DATA_MODE."""

from __future__ import annotations

from app.core.config import settings
from app.ingestion.base import MarketDataProvider
from app.ingestion.live import LiveMarketDataProvider
from app.ingestion.mock import MockMarketDataProvider
from app.ingestion.replay import ReplayMarketDataProvider
from app.ingestion.yahoo import YahooFinanceMarketDataProvider


def get_market_data_provider() -> MarketDataProvider:
    mode = (settings.market_data_mode or "replay").lower()
    if mode in {"yahoo", "yfinance"}:
        return YahooFinanceMarketDataProvider()
    if mode == "live":
        # Demo live-sim tape (not a licensed exchange feed)
        return LiveMarketDataProvider()
    if mode == "mock":
        return MockMarketDataProvider()
    return ReplayMarketDataProvider()
