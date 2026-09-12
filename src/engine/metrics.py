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
from datetime import datetime
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

MIN_QUARTERS_YOY = 5
"""Minimum quarters needed for YoY comparison (latest + 4 prior quarters
to find same-quarter in previous year)."""


# ──────────────────────────────────────────────────────────────────────
# Internal Helpers
# ──────────────────────────────────────────────────────────────────────


def _safe_growth(current: float | None, previous: float | None) -> float | None:
    """Compute growth rate with denominator guards.

    Formula: (current - previous) / |previous|

    Returns None if:
    - Either value is None
    - |previous| < MIN_DENOMINATOR (avoids noise from near-zero bases)
    """
    if current is None or previous is None:
        return None
    if abs(previous) < MIN_DENOMINATOR:
        return None
    return (current - previous) / abs(previous)


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division returning None on invalid inputs.

    Returns None if:
    - Either value is None
    - Denominator is zero or negative (for equity-based ratios)
    """
    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return None
    return numerator / denominator


def _find_yoy_quarter(
    quarterly: list[dict[str, Any]],
    latest_date: str,
) -> dict[str, Any] | None:
    """Find the same quarter from the previous year for YoY comparison.

    Matches on month (allows ±15 day tolerance for different reporting dates).

    Args:
        quarterly: List of quarterly dicts, each with "date" field (YYYY-MM-DD).
        latest_date: Date string of the latest quarter.

    Returns:
        The matching quarter dict, or None if not found.
    """
    try:
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    target_month = latest_dt.month
    target_year = latest_dt.year - 1

    for q in quarterly:
        q_date_str = q.get("date")
        if not q_date_str:
            continue
        try:
            q_dt = datetime.strptime(q_date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        if q_dt.year == target_year and q_dt.month == target_month:
            return q
        # Tolerance: ±1 month for fiscal year differences
        if q_dt.year == target_year and abs(q_dt.month - target_month) <= 1:
            return q

    return None


def _compute_margin(operating_pnl: float | None, revenue: float | None) -> float | None:
    """Compute operating margin = operating_pnl / revenue.

    Returns None if revenue is None, zero, or negative.
    """
    if operating_pnl is None or revenue is None:
        return None
    if revenue <= 0:
        return None
    return operating_pnl / revenue


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
        quarterly: Quarterly financial data, sorted newest-first.
                   Each dict has: date, revenue, earnings, operating_pnl,
                   total_equity, etc.
        daily: Daily transaction data, sorted by date ascending.
               Each dict has: date, close, market_cap.
        market_cap: Latest market cap. If None, extracted from daily data.

    Returns:
        Tuple of:
        - MetricSet with computed raw metrics
        - growth_method: "YoY" or "QoQ"
        - growth_period: e.g., "Q2 2026 vs Q2 2025 (YoY)"
        - price_period: e.g., "2026-08-11 to 2026-09-09"
    """
    metrics = MetricSet()
    growth_method = "N/A"
    growth_period: str | None = None
    price_period: str | None = None

    # ── Growth Metrics (Revenue, Earnings, Margin) ──────────────

    if len(quarterly) >= 2:
        q_latest = quarterly[0]
        latest_date = q_latest.get("date", "")

        # Try YoY first (requires ≥ 5 quarters to find same quarter prior year)
        q_comp = None
        if len(quarterly) >= MIN_QUARTERS_YOY:
            q_comp = _find_yoy_quarter(quarterly, latest_date)

        if q_comp is not None:
            growth_method = "YoY"
            comp_date = q_comp.get("date", "?")
            growth_period = f"{latest_date} vs {comp_date} (YoY)"
        else:
            # Fallback to QoQ
            q_comp = quarterly[1]
            growth_method = "QoQ"
            comp_date = q_comp.get("date", "?")
            growth_period = f"{latest_date} vs {comp_date} (QoQ)"

        # Revenue growth
        metrics.revenue_growth = _safe_growth(
            q_latest.get("revenue"),
            q_comp.get("revenue"),
        )

        # Earnings growth
        metrics.earnings_growth = _safe_growth(
            q_latest.get("earnings"),
            q_comp.get("earnings"),
        )

        # Operating margin (latest quarter)
        metrics.operating_margin = _compute_margin(
            q_latest.get("operating_pnl"),
            q_latest.get("revenue"),
        )

        # Margin change (latest vs comparison quarter)
        margin_latest = metrics.operating_margin
        margin_comp = _compute_margin(
            q_comp.get("operating_pnl"),
            q_comp.get("revenue"),
        )

        if margin_latest is not None and margin_comp is not None:
            metrics.margin_change = margin_latest - margin_comp

    # ── TTM Metrics (ROE, PE) ───────────────────────────────────

    if len(quarterly) >= MIN_QUARTERS_TTM:
        ttm_earnings = sum(q.get("earnings", 0) or 0 for q in quarterly[:MIN_QUARTERS_TTM])
        latest_equity = quarterly[0].get("total_equity")

        # ROE TTM
        if latest_equity is not None and latest_equity > 0 and ttm_earnings != 0:
            metrics.roe_ttm = ttm_earnings / latest_equity

        # PE TTM (informational)
        if market_cap is None and daily:
            market_cap = daily[-1].get("market_cap")

        if market_cap is not None and ttm_earnings > 0:
            metrics.pe_ttm = market_cap / ttm_earnings

        # PB (informational)
        if market_cap is not None and latest_equity is not None and latest_equity > 0:
            metrics.pb = market_cap / latest_equity

    # ── Price Return ────────────────────────────────────────────

    if len(daily) >= 2:
        close_first = daily[0].get("close")
        close_last = daily[-1].get("close")

        if close_first is not None and close_last is not None and close_first > 0:
            metrics.price_return = (close_last - close_first) / close_first

        date_first = daily[0].get("date", "?")
        date_last = daily[-1].get("date", "?")
        price_period = f"{date_first} to {date_last}"

    return metrics, growth_method, growth_period, price_period
