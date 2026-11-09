"""Abstract base interfaces and exceptions for financial market data and news providers."""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, ProviderCoverageReport, TickerInfo


class ProviderException(Exception):
    """Base exception for all financial provider integrations."""
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code or "PROVIDER_ERROR"


class AuthenticationError(ProviderException):
    """Raised when an API key is missing, invalid, or unauthorized."""
    def __init__(self, provider: str, message: str = "Invalid or missing API key."):
        super().__init__(message, provider, "AUTHENTICATION_FAILED")


class RateLimitExceeded(ProviderException):
    """Raised when provider returns HTTP 429 or client-side throttle is breached."""
    def __init__(self, provider: str, retry_after_sec: Optional[int] = None):
        msg = f"Rate limit exceeded for provider '{provider}'."
        if retry_after_sec:
            msg += f" Retry after {retry_after_sec} seconds."
        super().__init__(msg, provider, "RATE_LIMIT_EXCEEDED")
        self.retry_after_sec = retry_after_sec


class NetworkTimeoutError(ProviderException):
    """Raised when request times out after bounded retries."""
    def __init__(self, provider: str, timeout_sec: float):
        super().__init__(f"Request timed out after {timeout_sec}s for provider '{provider}'.", provider, "TIMEOUT")
        self.timeout_sec = timeout_sec


class CoverageLimitation(ProviderException):
    """Raised when requested date range or asset exceeds provider coverage."""
    def __init__(self, provider: str, detail: str):
        super().__init__(f"Coverage limitation for '{provider}': {detail}", provider, "COVERAGE_LIMITATION")


class TickerNotFoundError(ProviderException):
    """Raised when requested symbol cannot be resolved."""
    def __init__(self, provider: str, symbol: str):
        super().__init__(f"Ticker symbol '{symbol}' not found on '{provider}'.", provider, "TICKER_NOT_FOUND")
        self.symbol = symbol


class BaseTickerProvider(ABC):
    """Interface for stock and ETF symbol resolution and metadata."""

    @abstractmethod
    def validate_ticker(self, symbol: str) -> TickerInfo:
        """Validate whether a ticker is a recognized US equity or ETF."""
        pass

    @abstractmethod
    def search_tickers(self, query: str) -> List[TickerInfo]:
        """Search available tickers matching query string."""
        pass


class BaseMarketDataProvider(ABC):
    """Interface for historical market pricing and volume retrieval."""

    @abstractmethod
    def fetch_historical_prices(
        self,
        symbol: str,
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
    ) -> List[CanonicalPriceBar]:
        """Fetch daily OHLCV bars bounded by start_date and end_date."""
        pass

    @abstractmethod
    def get_coverage(self) -> ProviderCoverageReport:
        """Return provider coverage details and terms."""
        pass


class BaseNewsProvider(ABC):
    """Interface for financial news retrieval and normalization."""

    @abstractmethod
    def fetch_news(
        self,
        tickers: List[str],
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
    ) -> List[CanonicalNewsItem]:
        """Fetch and normalize financial news articles bounded by start_date and end_date."""
        pass

    @abstractmethod
    def get_coverage(self) -> ProviderCoverageReport:
        """Return news provider coverage details and limitations."""
        pass

