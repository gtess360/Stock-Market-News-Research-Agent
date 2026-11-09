"""Time-to-live caching layer for financial market data and news responses."""
import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

DEFAULT_NEWS_TTL_SEC = 300  # 5 minutes for live/historical news queries
DEFAULT_MARKET_DATA_TTL_SEC = 3600  # 1 hour for daily historical bars


class FinancialDataCache:
    """Thread-safe in-memory cache with configurable TTL per category."""

    def __init__(self):
        self._store: Dict[str, Tuple[float, Any]] = {}

    def _generate_key(self, provider: str, category: str, params: Dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True)
        raw_key = f"{provider}:{category}:{param_str}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, provider: str, category: str, params: Dict[str, Any]) -> Optional[Any]:
        key = self._generate_key(provider, category, params)
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, data = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return data

    def set(
        self,
        provider: str,
        category: str,
        params: Dict[str, Any],
        data: Any,
        ttl_sec: Optional[int] = None,
    ) -> None:
        if ttl_sec is None:
            ttl_sec = DEFAULT_MARKET_DATA_TTL_SEC if category == "market_data" else DEFAULT_NEWS_TTL_SEC
        key = self._generate_key(provider, category, params)
        expires_at = time.time() + ttl_sec
        self._store[key] = (expires_at, data)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# Global default cache singleton
default_cache = FinancialDataCache()

