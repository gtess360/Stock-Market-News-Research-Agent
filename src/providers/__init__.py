"""Financial market data and news providers package."""
from src.providers.base import (
    AuthenticationError,
    BaseMarketDataProvider,
    BaseNewsProvider,
    BaseTickerProvider,
    CoverageLimitation,
    NetworkTimeoutError,
    ProviderException,
    RateLimitExceeded,
    TickerNotFoundError,
)
from src.providers.cache import FinancialDataCache, default_cache
from src.providers.date_filter import get_market_current_date, is_trading_day, resolve_date_window
from src.providers.deduplication import deduplicate_news_articles
from src.providers.factory import ProviderFactory
from src.providers.live_adapters import AlphaVantageAdapter, FinnhubAdapter
from src.providers.mock_provider import MockFinancialDataProvider

__all__ = [
    "BaseTickerProvider",
    "BaseMarketDataProvider",
    "BaseNewsProvider",
    "ProviderException",
    "AuthenticationError",
    "RateLimitExceeded",
    "NetworkTimeoutError",
    "CoverageLimitation",
    "TickerNotFoundError",
    "MockFinancialDataProvider",
    "FinnhubAdapter",
    "AlphaVantageAdapter",
    "ProviderFactory",
    "FinancialDataCache",
    "default_cache",
    "resolve_date_window",
    "get_market_current_date",
    "is_trading_day",
    "deduplicate_news_articles",
]

