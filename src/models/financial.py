"""Canonical data models for financial market data, financial news, and provider metadata."""
from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CanonicalPriceBar(BaseModel):
    """Canonical data contract for OHLCV market pricing data."""
    ticker: str
    trading_date: str  # YYYY-MM-DD format
    open: float = Field(ge=0.0)
    high: float = Field(ge=0.0)
    low: float = Field(ge=0.0)
    close: float = Field(ge=0.0)
    adjusted_close: Optional[float] = Field(default=None, ge=0.0)
    volume: float = Field(ge=0.0)
    data_provider: str
    retrieved_at_utc: str
    delayed_flag: bool = True
    exchange_timezone: str = "America/New_York"

    @property
    def symbol(self) -> str:
        """Alias for ticker symbol."""
        return self.ticker

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def validate_high_low_prices(self) -> "CanonicalPriceBar":
        if self.high < self.low:
            raise ValueError(f"High price ({self.high}) cannot be less than low price ({self.low}).")
        return self


class CanonicalNewsItem(BaseModel):
    """Canonical data contract for verified financial news articles."""
    article_id: str
    ticker_association: List[str]
    headline: str
    publisher: str
    source_url: str
    published_at_utc: str  # ISO 8601 UTC format
    retrieved_at_utc: str  # ISO 8601 UTC format
    summary_or_description: Optional[str] = None
    provider_identification: str
    content_availability: Literal["full_text", "summary_only", "headline_only"] = "summary_only"
    language: str = "en"
    syndication_group: Optional[str] = None
    is_duplicate: bool = False
    canonical_article_id: Optional[str] = None
    evidence_flags: List[str] = Field(default_factory=list)

    @property
    def ticker_symbols(self) -> List[str]:
        """Alias for ticker_association."""
        return self.ticker_association

    @property
    def summary_if_licensed(self) -> Optional[str]:
        """Alias for summary_or_description."""
        return self.summary_or_description

    @field_validator("ticker_association")
    @classmethod
    def normalize_tickers(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip().upper() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("At least one valid ticker symbol is required.")
        return sorted(list(set(cleaned)))

    @field_validator("published_at_utc", "retrieved_at_utc")
    @classmethod
    def validate_iso_timestamps(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e
        return v


class TickerInfo(BaseModel):
    """Ticker resolution and metadata contract."""
    symbol: str
    name: str
    asset_type: Literal["equity", "etf", "index", "other"] = "equity"
    exchange: str = "US"
    currency: str = "USD"
    is_valid: bool = True


class ProviderCoverageReport(BaseModel):
    """Metadata detailing provider capabilities, terms, and constraints."""
    provider_name: str
    news_supported: bool
    market_data_supported: bool
    historical_news_days_limit: int
    market_data_delay_minutes: int
    rate_limit_per_minute: int
    commercial_redistribution_allowed: bool
    attribution_notice_required: str
