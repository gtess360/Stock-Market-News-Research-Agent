"""Historical timeline filtering and point-in-time guardrails."""
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional, Tuple
from zoneinfo import ZoneInfo

MARKET_TIMEZONE = ZoneInfo("America/New_York")
PRESETS = ("Today", "7D", "30D", "90D", "Custom")
PresetType = Literal["Today", "7D", "30D", "90D", "Custom"]


def get_market_current_date() -> date:
    """Get the current calendar date in the US equity market timezone (America/New_York)."""
    return datetime.now(MARKET_TIMEZONE).date()


def resolve_date_window(
    preset: PresetType | str,
    custom_start: Optional[str | date] = None,
    custom_end: Optional[str | date] = None,
    as_of: Optional[str | date] = None,
) -> Tuple[str, str]:
    """Resolve human-readable historical presets to strictly validated YYYY-MM-DD date bounds.
    
    Args:
        preset: 'Today', '7D', '30D', '90D', or 'Custom'
        custom_start: ISO date string or date object if preset is 'Custom'
        custom_end: ISO date string or date object if preset is 'Custom'
        as_of: Reference point-in-time cutoff date (defaults to market current date)
        
    Returns:
        Tuple[str, str]: (start_date_str, end_date_str) in 'YYYY-MM-DD'
        
    Raises:
        ValueError: If start > end, if dates exceed as_of (look-ahead leak), or invalid preset.
    """
    if as_of is None:
        cutoff = get_market_current_date()
    elif isinstance(as_of, str):
        cutoff = date.fromisoformat(as_of)
    else:
        cutoff = as_of

    clean_preset = preset.strip()

    if clean_preset == "Today":
        start_dt = cutoff
        end_dt = cutoff
    elif clean_preset in ("7D", "7d", "Last 7 days"):
        start_dt = cutoff - timedelta(days=7)
        end_dt = cutoff
    elif clean_preset in ("30D", "30d", "Last 30 days"):
        start_dt = cutoff - timedelta(days=30)
        end_dt = cutoff
    elif clean_preset in ("90D", "90d", "Last 90 days"):
        start_dt = cutoff - timedelta(days=90)
        end_dt = cutoff
    elif clean_preset in ("Custom", "custom"):
        if not custom_start or not custom_end:
            raise ValueError("Custom preset requires both custom_start and custom_end dates.")
        start_dt = date.fromisoformat(str(custom_start)) if isinstance(custom_start, str) else custom_start
        end_dt = date.fromisoformat(str(custom_end)) if isinstance(custom_end, str) else custom_end
    else:
        raise ValueError(f"Unknown date window preset: '{preset}'. Valid presets: {PRESETS}")

    # Point-in-time and integrity guardrails
    if start_dt > end_dt:
        raise ValueError(f"start_date ({start_dt.isoformat()}) cannot be after end_date ({end_dt.isoformat()}).")

    if end_dt > cutoff:
        raise ValueError(
            f"Point-in-time guardrail violation: end_date ({end_dt.isoformat()}) exceeds as-of evaluation date ({cutoff.isoformat()}). Look-ahead leakage is prohibited."
        )

    return start_dt.isoformat(), end_dt.isoformat()


def is_trading_day(d: date) -> bool:
    """Return True if date falls on a standard Monday-Friday trading session."""
    return d.weekday() < 5

