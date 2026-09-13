"""Financial metrics calculator for Market State Engine (Task T2.2).

Computes 6 raw metrics + 2 informational metrics from Sectors API data:

Core (used in peer_z normalization):
1. revenue_growth     — YoY with QoQ fallback
2. earnings_growth    — YoY with QoQ fallback
3. operating_margin   — operating_pnl / revenue
4. margin_change      — margin(Q_latest) - margin(Q_comp) in pp
5. roe_ttm            — TTM earnings / latest equity
6. price_return       — (close_last - close_first) / close_first

Informational (displayed in memo, not in discrepancy formula):
7. pe_ttm             — market_cap / TTM earnings
8. pb                 — market_cap / total_equity

Edge-case guards:
- Division by zero → None
- Negative equity → None for ROE, PB
- TTM earnings ≤ 0 → None for PE
- Insufficient data → None with log warning
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

from src.engine.models import MetricSet

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

MIN_DENOMINATOR = 1_000_000
"""Minimum absolute denominator (Rp 1M) to avoid noise from micro-cap
or near-zero revenue/earnings producing misleading growth rates."""

MIN_QUARTERS_TTM = 4
"""Minimum quarters needed for TTM (Trailing Twelve Months) calculation."""

# ──────────────────────────────────────────────────────────────────────
# Internal Helpers
# ──────────────────────────────────────────────────────────────────────


def _finite_number(value: object) -> float | int | None:
    """Return a finite int/float, never coercing API values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, int):
        return value
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _parse_date(value: object) -> date | None:
    """Parse the strict ISO reporting-date contract."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _safe_growth(current: float | None, previous: float | None) -> float | None:
    """Compute growth rate with denominator guards.

    Formula: (current - previous) / |previous|

    Returns None if:
    - Either value is None
    - |previous| < MIN_DENOMINATOR (avoids noise from near-zero bases)
    """
    current = _finite_number(current)
    previous = _finite_number(previous)
    if current is None or previous is None:
        return None
    if abs(previous) < MIN_DENOMINATOR:
        return None
    try:
        result = (current - previous) / abs(previous)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division returning None on invalid inputs.

    Returns None if:
    - Either value is None
    - Denominator is zero or negative (for equity-based ratios)
    """
    numerator = _finite_number(numerator)
    denominator = _finite_number(denominator)
    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return None
    try:
        result = numerator / denominator
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _find_yoy_quarter(
    quarterly: list[dict[str, Any]],
    latest_date: str,
) -> dict[str, Any] | None:
    """Find the exact same reporting month from the previous year.

    Args:
        quarterly: List of quarterly dicts, each with "date" field (YYYY-MM-DD).
        latest_date: Date string of the latest quarter.

    Returns:
        The matching quarter dict, or None if not found.
    """
    latest_dt = _parse_date(latest_date)
    if latest_dt is None:
        return None

    target_month = latest_dt.month
    target_year = latest_dt.year - 1

    for q in quarterly:
        q_dt = _parse_date(q.get("date"))
        if q_dt is None:
            continue

        if q_dt.year == target_year and q_dt.month == target_month:
            return q

    return None


def _compute_margin(operating_pnl: float | None, revenue: float | None) -> float | None:
    """Compute operating margin = operating_pnl / revenue.

    Returns None if revenue is None, zero, or negative.
    """
    operating_pnl = _finite_number(operating_pnl)
    revenue = _finite_number(revenue)
    if operating_pnl is None or revenue is None:
        return None
    if revenue <= 0:
        return None
    try:
        result = operating_pnl / revenue
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _validated_quarters(quarterly: list[dict[str, Any]]) -> list[tuple[date, dict[str, Any]]]:
    """Accept unique ISO-dated quarterly observations, newest first."""
    validated: list[tuple[date, dict[str, Any]]] = []
    seen_dates: set[date] = set()
    for quarter in quarterly:
        if not isinstance(quarter, dict):
            return []
        report_date = _parse_date(quarter.get("date"))
        if report_date is None or report_date in seen_dates:
            return []
        validated.append((report_date, quarter))
        seen_dates.add(report_date)
    return sorted(validated, key=lambda item: item[0], reverse=True)


def _validated_daily(daily: list[dict[str, Any]]) -> list[tuple[date, dict[str, Any]]]:
    """Accept unique ISO-dated daily observations, oldest first."""
    validated: list[tuple[date, dict[str, Any]]] = []
    seen_dates: set[date] = set()
    for observation in daily:
        if not isinstance(observation, dict):
            return []
        observation_date = _parse_date(observation.get("date"))
        if observation_date is None or observation_date in seen_dates:
            return []
        validated.append((observation_date, observation))
        seen_dates.add(observation_date)
    return sorted(validated, key=lambda item: item[0])


def _are_adjacent_quarters(newer: date, older: date) -> bool:
    """Whether two reporting dates are one calendar quarter apart."""
    return (newer.year * 12 + newer.month) - (older.year * 12 + older.month) == 3


# ──────────────────────────────────────────────────────────────────────
# Main Calculator
# ──────────────────────────────────────────────────────────────────────


def calculate_metrics(
    quarterly: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    market_cap: float | None = None,
) -> tuple[MetricSet, str, str | None, str | None]:
    """Compute raw financial metrics from Sectors API data.

    Args:
        quarterly: Quarterly financial data with unique ISO dates.
                   Each dict has: date, revenue, earnings, operating_pnl,
                   total_equity, etc.
        daily: Daily transaction data with unique ISO dates.
               Each dict has: date, close, market_cap.
        market_cap: Latest market cap. If None, extracted from daily data.

    Returns:
        Tuple of:
        - MetricSet with computed raw metrics
        - growth_method: "YoY", "QoQ", or "N/A"
        - growth_period: e.g., "Q2 2026 vs Q2 2025 (YoY)"
        - price_period: e.g., "2026-08-11 to 2026-09-09"
    """
    metrics = MetricSet()
    growth_method = "N/A"
    growth_period: str | None = None
    price_period: str | None = None

    validated = _validated_quarters(quarterly)
    validated_daily = _validated_daily(daily)
    latest = validated[0][1] if validated else None
    latest_date = validated[0][0] if validated else None

    latest_market_cap = _finite_number(market_cap)
    if latest_market_cap is None and validated_daily:
        latest_market_cap = _finite_number(validated_daily[-1][1].get("market_cap"))

    # These latest-period ratios do not require comparison or TTM history.
    if latest is not None:
        metrics.operating_margin = _compute_margin(
            latest.get("operating_pnl"), latest.get("revenue")
        )
        latest_equity = _finite_number(latest.get("total_equity"))
        if latest_market_cap is not None and latest_market_cap >= 0:
            metrics.pb = _safe_divide(latest_market_cap, latest_equity)
    else:
        latest_equity = None

    # ── Growth Metrics (YoY first, then only adjacent QoQ) ──────
    if latest is not None and latest_date is not None and len(validated) >= 2:
        q_comp = _find_yoy_quarter([q for _, q in validated], latest.get("date", ""))
        if q_comp is not None:
            growth_method = "YoY"
        elif _are_adjacent_quarters(latest_date, validated[1][0]):
            q_comp = validated[1][1]
            growth_method = "QoQ"

        if q_comp is not None:
            comp_date = q_comp["date"]
            growth_period = f"{latest['date']} vs {comp_date} ({growth_method})"
            metrics.revenue_growth = _safe_growth(latest.get("revenue"), q_comp.get("revenue"))
            metrics.earnings_growth = _safe_growth(latest.get("earnings"), q_comp.get("earnings"))
            margin_comp = _compute_margin(q_comp.get("operating_pnl"), q_comp.get("revenue"))
            if metrics.operating_margin is not None and margin_comp is not None:
                change = metrics.operating_margin - margin_comp
                metrics.margin_change = change if math.isfinite(change) else None

    # ── TTM Metrics (ROE, PE) ───────────────────────────────────
    ttm_quarters = validated[:MIN_QUARTERS_TTM]
    if len(ttm_quarters) == MIN_QUARTERS_TTM and all(
        _are_adjacent_quarters(ttm_quarters[i][0], ttm_quarters[i + 1][0])
        for i in range(MIN_QUARTERS_TTM - 1)
    ):
        earnings = [_finite_number(q.get("earnings")) for _, q in ttm_quarters]
        if all(value is not None for value in earnings):
            ttm_earnings = sum(earnings)
            metrics.roe_ttm = _safe_divide(ttm_earnings, latest_equity)
            if latest_market_cap is not None and latest_market_cap >= 0 and ttm_earnings > 0:
                metrics.pe_ttm = _safe_divide(latest_market_cap, ttm_earnings)

    # ── Price Return ────────────────────────────────────────────

    if len(validated_daily) >= 2:
        first_date, first = validated_daily[0]
        last_date, last = validated_daily[-1]
        if first_date < last_date:
            price_period = f"{first['date']} to {last['date']}"
            close_first = _finite_number(first.get("close"))
            close_last = _finite_number(last.get("close"))
            if close_first is not None and close_last is not None and close_first > 0 and close_last >= 0:
                try:
                    result = (close_last - close_first) / close_first
                except OverflowError:
                    result = None
                metrics.price_return = result if result is not None and math.isfinite(result) else None

    return metrics, growth_method, growth_period, price_period
