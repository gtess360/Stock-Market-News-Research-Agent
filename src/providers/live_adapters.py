"""Production-grade external financial data adapters with exponential backoff, rate limit handling, and canonical mapping."""
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import requests
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, ProviderCoverageReport, TickerInfo
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

DEFAULT_TIMEOUT_SEC = 10.0
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 0.5


def request_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    provider: str = "ExternalAPI",
    timeout: float = DEFAULT_TIMEOUT_SEC,
    max_retries: int = MAX_RETRIES,
) -> requests.Response:
    """Execute HTTP GET with bounded exponential backoff and rate limit handling."""
    delay = INITIAL_BACKOFF_SEC
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Rate limit handling (HTTP 429)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_sec = int(retry_after) if retry_after and retry_after.isdigit() else int(delay * 2)
                if attempt == max_retries - 1:
                    raise RateLimitExceeded(provider=provider, retry_after_sec=wait_sec)
                time.sleep(min(wait_sec, 5))
                continue

            # Authentication failures
            if resp.status_code in (401, 403):
                raise AuthenticationError(provider=provider, message=f"Authentication failed: {resp.text[:100]}")

            # Server errors (5xx)
            if 500 <= resp.status_code < 600:
                if attempt == max_retries - 1:
                    resp.raise_for_status()
                time.sleep(delay)
                delay *= 2
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout as e:
            if attempt == max_retries - 1:
                raise NetworkTimeoutError(provider=provider, timeout_sec=timeout) from e
            time.sleep(delay)
            delay *= 2
        except requests.exceptions.RequestException as e:
            if isinstance(e, (RateLimitExceeded, AuthenticationError, NetworkTimeoutError)):
                raise
            if attempt == max_retries - 1:
                raise ProviderException(message=f"HTTP request failed: {str(e)}", provider=provider) from e
            time.sleep(delay)
            delay *= 2

    raise ProviderException(f"Failed to execute request after {max_retries} attempts.", provider=provider)


class FinnhubAdapter(BaseNewsProvider, BaseMarketDataProvider, BaseTickerProvider):
    """Adapter for Finnhub.io REST APIs (Company News, Candles, Search)."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")

    def _require_key(self) -> str:
        if not self.api_key:
            raise AuthenticationError(
                provider="Finnhub",
                message="FINNHUB_API_KEY environment variable is not configured.",
            )
        return self.api_key

    def get_coverage(self) -> ProviderCoverageReport:
        return ProviderCoverageReport(
            provider_name="Finnhub",
            news_supported=True,
            market_data_supported=True,
            historical_news_days_limit=365,  # Up to 1 year on paid tiers; ~30-60d on free
            market_data_delay_minutes=15,
            rate_limit_per_minute=60,  # 60 calls/min on free tier
            commercial_redistribution_allowed=False,  # Display only, check license terms
            attribution_notice_required="Data provided by Finnhub.io.",
        )

    def validate_ticker(self, symbol: str) -> TickerInfo:
        key = self._require_key()
        clean = symbol.strip().upper()
        url = f"{self.BASE_URL}/search"
        resp = request_with_retry(url, params={"q": clean, "token": key}, provider="Finnhub")
        data = resp.json()
        matches = data.get("result", [])
        for m in matches:
            if m.get("symbol", "").upper() == clean:
                return TickerInfo(
                    symbol=clean,
                    name=m.get("description", clean),
                    asset_type="equity" if "stock" in m.get("type", "").lower() else "etf",
                    exchange="US",
                    is_valid=True,
                )
        return TickerInfo(symbol=clean, name="Unknown", asset_type="other", exchange="UNKNOWN", is_valid=False)

    def search_tickers(self, query: str) -> List[TickerInfo]:
        key = self._require_key()
        url = f"{self.BASE_URL}/search"
        resp = request_with_retry(url, params={"q": query, "token": key}, provider="Finnhub")
        data = resp.json()
        results = []
        for m in data.get("result", []):
            results.append(
                TickerInfo(
                    symbol=m.get("symbol", "").upper(),
                    name=m.get("description", ""),
                    asset_type="equity",
                    exchange="US",
                    is_valid=True,
                )
            )
        return results

    def fetch_news(self, tickers: List[str], start_date: str, end_date: str) -> List[CanonicalNewsItem]:
        key = self._require_key()
        now_utc = datetime.now(timezone.utc).isoformat()
        results: List[CanonicalNewsItem] = []

        for ticker in tickers:
            clean = ticker.strip().upper()
            url = f"{self.BASE_URL}/company-news"
            params = {"symbol": clean, "from": start_date, "to": end_date, "token": key}
            resp = request_with_retry(url, params=params, provider="Finnhub")
            raw_items = resp.json()

            for item in raw_items:
                epoch = item.get("datetime", 0)
                pub_iso = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
                art_id = str(item.get("id", f"fh_{clean}_{epoch}"))
                headline = item.get("headline", "").strip()
                if not headline:
                    continue

                results.append(
                    CanonicalNewsItem(
                        article_id=art_id,
                        ticker_association=[clean],
                        headline=headline,
                        publisher=item.get("source", "Finnhub Source"),
                        source_url=item.get("url", ""),
                        published_at_utc=pub_iso,
                        retrieved_at_utc=now_utc,
                        summary_or_description=item.get("summary"),
                        provider_identification="Finnhub",
                        content_availability="summary_only",
                    )
                )

        results.sort(key=lambda x: x.published_at_utc, reverse=True)
        return results

    def fetch_historical_prices(self, symbol: str, start_date: str, end_date: str) -> List[CanonicalPriceBar]:
        key = self._require_key()
        clean = symbol.strip().upper()
        now_utc = datetime.now(timezone.utc).isoformat()

        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        start_ts = int(datetime(start_dt.year, start_dt.month, start_dt.day, tzinfo=timezone.utc).timestamp())
        end_ts = int(datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59, tzinfo=timezone.utc).timestamp())

        url = f"{self.BASE_URL}/stock/candle"
        params = {"symbol": clean, "resolution": "D", "from": start_ts, "to": end_ts, "token": key}
        try:
            resp = request_with_retry(url, params=params, provider="Finnhub")
            data = resp.json()
        except AuthenticationError as e:
            # Finnhub free tier restricts /stock/candle for US equities.
            # Gracefully fallback to /quote to provide current trading bar.
            quote_url = f"{self.BASE_URL}/quote"
            try:
                q_resp = request_with_retry(quote_url, params={"symbol": clean, "token": key}, provider="Finnhub")
                q_data = q_resp.json()
                if q_data and q_data.get("c", 0) > 0:
                    ts = q_data.get("t") or int(time.time())
                    trading_d = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                    return [
                        CanonicalPriceBar(
                            ticker=clean,
                            trading_date=trading_d,
                            open=float(q_data.get("o", q_data.get("c"))),
                            high=float(q_data.get("h", q_data.get("c"))),
                            low=float(q_data.get("l", q_data.get("c"))),
                            close=float(q_data.get("c")),
                            volume=0.0,
                            data_provider="Finnhub",
                            retrieved_at_utc=now_utc,
                            delayed_flag=True,
                        )
                    ]
            except Exception:
                pass
            raise

        if data.get("s") == "no_data":
            return []

        c_list = data.get("c", [])
        h_list = data.get("h", [])
        l_list = data.get("l", [])
        o_list = data.get("o", [])
        t_list = data.get("t", [])
        v_list = data.get("v", [])

        bars: List[CanonicalPriceBar] = []
        for i in range(len(t_list)):
            trading_d = datetime.fromtimestamp(t_list[i], tz=timezone.utc).date().isoformat()
            bars.append(
                CanonicalPriceBar(
                    ticker=clean,
                    trading_date=trading_d,
                    open=float(o_list[i]),
                    high=float(h_list[i]),
                    low=float(l_list[i]),
                    close=float(c_list[i]),
                    volume=float(v_list[i]),
                    data_provider="Finnhub",
                    retrieved_at_utc=now_utc,
                    delayed_flag=True,
                )
            )

        bars.sort(key=lambda b: b.trading_date)
        return bars


class AlphaVantageAdapter(BaseNewsProvider, BaseMarketDataProvider):
    """Adapter for Alpha Vantage (NEWS_SENTIMENT and TIME_SERIES_DAILY)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")

    def _require_key(self) -> str:
        if not self.api_key:
            raise AuthenticationError(
                provider="AlphaVantage",
                message="ALPHA_VANTAGE_API_KEY environment variable is not configured.",
            )
        return self.api_key

    def get_coverage(self) -> ProviderCoverageReport:
        return ProviderCoverageReport(
            provider_name="AlphaVantage",
            news_supported=True,
            market_data_supported=True,
            historical_news_days_limit=90,
            market_data_delay_minutes=15,
            rate_limit_per_minute=5,  # Free tier is heavily throttled (5 calls/min)
            commercial_redistribution_allowed=False,
            attribution_notice_required="Data provided by Alpha Vantage.",
        )

    def fetch_news(self, tickers: List[str], start_date: str, end_date: str) -> List[CanonicalNewsItem]:
        key = self._require_key()
        now_utc = datetime.now(timezone.utc).isoformat()
        results: List[CanonicalNewsItem] = []

        ticker_param = ",".join([t.strip().upper() for t in tickers])
        # Format time_from as YYYYMMDDTHHMM
        time_from = start_date.replace("-", "") + "T0000"
        time_to = end_date.replace("-", "") + "T2359"

        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker_param,
            "time_from": time_from,
            "time_to": time_to,
            "limit": 50,
            "apikey": key,
        }
        resp = request_with_retry(self.BASE_URL, params=params, provider="AlphaVantage")
        data = resp.json()

        if "Note" in data:
            raise RateLimitExceeded(provider="AlphaVantage", retry_after_sec=60)
        if "Information" in data:
            info_msg = data.get("Information", "")
            if "premium" in info_msg.lower():
                raise CoverageLimitation(provider="AlphaVantage", detail=f"Alpha Vantage: {info_msg}")
            raise RateLimitExceeded(provider="AlphaVantage", retry_after_sec=60)

        for item in data.get("feed", []):
            pub_raw = item.get("time_published", "")
            # e.g. 20261025T143000 -> ISO
            try:
                dt = datetime.strptime(pub_raw, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                pub_iso = dt.isoformat()
            except Exception:
                pub_iso = now_utc

            results.append(
                CanonicalNewsItem(
                    article_id=f"av_{item.get('title', '')[:20]}_{pub_raw}",
                    ticker_association=[t.get("ticker", "") for t in item.get("ticker_sentiment", [])] or tickers,
                    headline=item.get("title", "").strip(),
                    publisher=item.get("source", "AlphaVantage Source"),
                    source_url=item.get("url", ""),
                    published_at_utc=pub_iso,
                    retrieved_at_utc=now_utc,
                    summary_or_description=item.get("summary"),
                    provider_identification="AlphaVantage",
                )
            )

        results.sort(key=lambda x: x.published_at_utc, reverse=True)
        return results

    def fetch_historical_prices(self, symbol: str, start_date: str, end_date: str) -> List[CanonicalPriceBar]:
        key = self._require_key()
        clean = symbol.strip().upper()
        now_utc = datetime.now(timezone.utc).isoformat()

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": clean,
            "outputsize": "compact",
            "apikey": key,
        }
        resp = request_with_retry(self.BASE_URL, params=params, provider="AlphaVantage")
        data = resp.json()

        if "Note" in data:
            raise RateLimitExceeded(provider="AlphaVantage", retry_after_sec=60)
        if "Information" in data:
            info_msg = data.get("Information", "")
            if "premium" in info_msg.lower():
                raise CoverageLimitation(provider="AlphaVantage", detail=f"Alpha Vantage: {info_msg}")
            raise RateLimitExceeded(provider="AlphaVantage", retry_after_sec=60)

        ts_data = data.get("Time Series (Daily)", {})
        bars: List[CanonicalPriceBar] = []

        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)

        for d_str, bar in ts_data.items():
            bar_date = date.fromisoformat(d_str)
            if start_dt <= bar_date <= end_dt:
                bars.append(
                    CanonicalPriceBar(
                        ticker=clean,
                        trading_date=d_str,
                        open=float(bar.get("1. open", 0.0)),
                        high=float(bar.get("2. high", 0.0)),
                        low=float(bar.get("3. low", 0.0)),
                        close=float(bar.get("4. close", 0.0)),
                        volume=float(bar.get("5. volume", 0.0)),
                        data_provider="AlphaVantage",
                        retrieved_at_utc=now_utc,
                        delayed_flag=True,
                    )
                )

        bars.sort(key=lambda b: b.trading_date)
        return bars

