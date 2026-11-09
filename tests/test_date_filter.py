"""Unit tests for historical date window resolution and point-in-time guardrails."""
from datetime import date
import pytest
from src.providers.date_filter import is_trading_day, resolve_date_window


def test_date_presets():
    """Verify standard date presets compute correct boundaries relative to reference date."""
    ref_date = date(2026, 11, 7)

    # Today
    s, e = resolve_date_window("Today", as_of=ref_date)
    assert s == "2026-11-07"
    assert e == "2026-11-07"

    # 7D
    s7, e7 = resolve_date_window("7D", as_of=ref_date)
    assert s7 == "2026-10-31"
    assert e7 == "2026-11-07"

    # 30D
    s30, e30 = resolve_date_window("30D", as_of=ref_date)
    assert s30 == "2026-10-08"
    assert e30 == "2026-11-07"

    # 90D
    s90, e90 = resolve_date_window("90D", as_of=ref_date)
    assert s90 == "2026-08-09"
    assert e90 == "2026-11-07"


def test_custom_date_window():
    """Verify custom date parsing."""
    ref_date = date(2026, 11, 7)
    s, e = resolve_date_window("Custom", custom_start="2026-09-01", custom_end="2026-10-15", as_of=ref_date)
    assert s == "2026-09-01"
    assert e == "2026-10-15"


def test_point_in_time_guardrail_rejection():
    """Verify rejection of future date leakage exceeding as-of reference date."""
    ref_date = date(2026, 11, 7)
    with pytest.raises(ValueError, match="Point-in-time guardrail violation"):
        resolve_date_window("Custom", custom_start="2026-11-01", custom_end="2026-11-15", as_of=ref_date)


def test_start_after_end_rejection():
    """Verify start date after end date is rejected."""
    ref_date = date(2026, 11, 7)
    with pytest.raises(ValueError, match="cannot be after end_date"):
        resolve_date_window("Custom", custom_start="2026-10-20", custom_end="2026-10-10", as_of=ref_date)


def test_trading_day_evaluation():
    """Verify weekday vs weekend classification."""
    monday = date(2026, 11, 2)
    friday = date(2026, 11, 6)
    saturday = date(2026, 11, 7)
    sunday = date(2026, 11, 8)

    assert is_trading_day(monday) is True
    assert is_trading_day(friday) is True
    assert is_trading_day(saturday) is False
    assert is_trading_day(sunday) is False

