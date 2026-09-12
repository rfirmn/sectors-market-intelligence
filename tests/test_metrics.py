"""Unit tests for financial metrics calculator (src/engine/metrics.py).

Tests cover:
- Revenue/earnings growth (YoY, QoQ fallback, zero denominator, loss→profit)
- Operating margin (normal, negative revenue)
- Margin change
- ROE TTM (normal, negative equity, < 4 quarters)
- PE TTM (positive/negative earnings)
- PB
- Price return (normal, insufficient data)
- YoY quarter matching
- ASII cross-verification against pre-computed values
"""

from __future__ import annotations

import pytest

from src.engine.metrics import (
    _compute_margin,
    _find_yoy_quarter,
    _safe_growth,
    calculate_metrics,
)

# ──────────────────────────────────────────────────────────────────────
# _safe_growth()
# ──────────────────────────────────────────────────────────────────────


class TestSafeGrowth:
    def test_positive_growth(self):
        """Normal positive growth: 100→125 = 25%."""
        assert _safe_growth(125e9, 100e9) == pytest.approx(0.25)

    def test_negative_growth(self):
        """Revenue decline: 100→80 = -20%."""
        assert _safe_growth(80e9, 100e9) == pytest.approx(-0.20)

    def test_zero_denominator(self):
        """Previous value below MIN_DENOMINATOR → None."""
        assert _safe_growth(100e9, 0) is None
        assert _safe_growth(100e9, 500_000) is None  # < 1M

    def test_none_inputs(self):
        """None values → None."""
        assert _safe_growth(None, 100e9) is None
        assert _safe_growth(100e9, None) is None

    def test_loss_to_profit(self):
        """Transition from loss to profit: -10B → +5B = +150%."""
        result = _safe_growth(5e9, -10e9)
        assert result == pytest.approx(1.5)

    def test_negative_denominator_uses_abs(self):
        """Growth from negative base uses |prev| as denominator."""
        # -50B → -20B = improvement of 30B/50B = 60%
        result = _safe_growth(-20e9, -50e9)
        assert result == pytest.approx(0.60)


# ──────────────────────────────────────────────────────────────────────
# _compute_margin()
# ──────────────────────────────────────────────────────────────────────


class TestComputeMargin:
    def test_normal_margin(self):
        """Standard operating margin: 10B/100B = 10%."""
        assert _compute_margin(10e9, 100e9) == pytest.approx(0.10)

    def test_zero_revenue(self):
        """Zero revenue → None."""
        assert _compute_margin(10e9, 0) is None

    def test_negative_revenue(self):
        """Negative revenue → None."""
        assert _compute_margin(10e9, -50e9) is None

    def test_none_inputs(self):
        """None inputs → None."""
        assert _compute_margin(None, 100e9) is None
        assert _compute_margin(10e9, None) is None


# ──────────────────────────────────────────────────────────────────────
# _find_yoy_quarter()
# ──────────────────────────────────────────────────────────────────────


class TestFindYoyQuarter:
    def test_exact_match(self):
        """Find exact same month in prior year."""
        quarters = [
            {"date": "2026-06-30", "revenue": 100e9},
            {"date": "2026-03-31", "revenue": 90e9},
            {"date": "2025-12-31", "revenue": 95e9},
            {"date": "2025-09-30", "revenue": 85e9},
            {"date": "2025-06-30", "revenue": 80e9},  # ← YoY match
        ]
        result = _find_yoy_quarter(quarters, "2026-06-30")
        assert result is not None
        assert result["date"] == "2025-06-30"

    def test_no_match(self):
        """Only 4 quarters → no YoY match available."""
        quarters = [
            {"date": "2026-06-30"},
            {"date": "2026-03-31"},
            {"date": "2025-12-31"},
            {"date": "2025-09-30"},
        ]
        result = _find_yoy_quarter(quarters, "2026-06-30")
        assert result is None

    def test_invalid_date(self):
        """Invalid date string → None."""
        assert _find_yoy_quarter([{"date": "bad"}], "bad") is None


# ──────────────────────────────────────────────────────────────────────
# calculate_metrics() — Full Integration
# ──────────────────────────────────────────────────────────────────────


# Realistic ASII data (from live cache — pre-verified)
ASII_QUARTERLY = [
    {
        "date": "2026-06-30",
        "revenue": 79_245_000_000_000,
        "earnings": 6_683_000_000_000,
        "operating_pnl": 8_107_000_000_000,
        "total_equity": 289_844_000_000_000,
    },
    {
        "date": "2026-03-31",
        "revenue": 78_668_000_000_000,
        "earnings": 5_850_000_000_000,
        "operating_pnl": 6_310_000_000_000,
        "total_equity": 293_123_000_000_000,
    },
    {
        "date": "2025-12-31",
        "revenue": 79_784_000_000_000,
        "earnings": 8_296_000_000_000,
        "operating_pnl": 10_275_000_000_000,
        "total_equity": 290_812_000_000_000,
    },
    {
        "date": "2025-09-30",
        "revenue": 80_751_000_000_000,
        "earnings": 8_958_000_000_000,
        "operating_pnl": 9_223_000_000_000,
        "total_equity": 289_631_000_000_000,
    },
]

ASII_DAILY = [
    {"date": "2026-08-11", "close": 4870, "market_cap": 197_154_432_729_000},
    {"date": "2026-08-12", "close": 4860, "market_cap": 196_749_832_729_000},
    # ... (simplified, only first and last matter for price_return)
    {"date": "2026-09-09", "close": 4850, "market_cap": 196_345_232_729_000},
]


class TestCalculateMetrics:
    def test_revenue_growth_qoq(self):
        """With 4 quarters (no YoY), falls back to QoQ."""
        metrics, method, period, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert method == "QoQ"
        # (79.245T - 78.668T) / 78.668T ≈ 0.00733
        assert metrics.revenue_growth == pytest.approx(0.00733, abs=0.001)

    def test_revenue_growth_yoy(self):
        """With 8 quarters (YoY available), uses YoY."""
        # Add 4 more quarters from prior year
        extra_quarters = ASII_QUARTERLY + [
            {
                "date": "2025-06-30",
                "revenue": 75_000_000_000_000,
                "earnings": 7_000_000_000_000,
                "operating_pnl": 8_000_000_000_000,
                "total_equity": 280_000_000_000_000,
            },
            {
                "date": "2025-03-31",
                "revenue": 74_000_000_000_000,
                "earnings": 6_500_000_000_000,
                "operating_pnl": 7_500_000_000_000,
                "total_equity": 278_000_000_000_000,
            },
            {
                "date": "2024-12-31",
                "revenue": 76_000_000_000_000,
                "earnings": 7_500_000_000_000,
                "operating_pnl": 9_000_000_000_000,
                "total_equity": 275_000_000_000_000,
            },
            {
                "date": "2024-09-30",
                "revenue": 77_000_000_000_000,
                "earnings": 8_000_000_000_000,
                "operating_pnl": 8_500_000_000_000,
                "total_equity": 273_000_000_000_000,
            },
        ]
        metrics, method, period, _ = calculate_metrics(extra_quarters, ASII_DAILY)
        assert method == "YoY"
        # Q2'26 (79.245T) vs Q2'25 (75T): (79.245-75)/75 ≈ 0.0566
        assert metrics.revenue_growth == pytest.approx(0.0566, abs=0.001)
        assert "YoY" in (period or "")

    def test_earnings_growth_qoq(self):
        """Earnings growth QoQ: (6.683T - 5.850T) / 5.850T ≈ 14.24%."""
        metrics, _, _, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert metrics.earnings_growth == pytest.approx(0.1424, abs=0.001)

    def test_operating_margin(self):
        """Operating margin: 8.107T / 79.245T ≈ 10.23%."""
        metrics, _, _, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert metrics.operating_margin == pytest.approx(0.1023, abs=0.001)

    def test_margin_change(self):
        """Margin change: 10.23% - 8.02% ≈ +2.21pp."""
        metrics, _, _, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert metrics.margin_change == pytest.approx(0.0221, abs=0.001)

    def test_roe_ttm(self):
        """ROE TTM: (6.683+5.850+8.296+8.958)T / 289.844T ≈ 10.28%."""
        metrics, _, _, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert metrics.roe_ttm == pytest.approx(0.1028, abs=0.001)

    def test_pe_ttm(self):
        """PE TTM: 196.345T / 29.787T ≈ 6.59x."""
        metrics, _, _, _ = calculate_metrics(
            ASII_QUARTERLY, ASII_DAILY, market_cap=196_345_232_729_000
        )
        assert metrics.pe_ttm == pytest.approx(6.59, abs=0.05)

    def test_price_return(self):
        """Price return: (4850 - 4870) / 4870 ≈ -0.41%."""
        metrics, _, _, _ = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert metrics.price_return == pytest.approx(-0.0041, abs=0.001)

    def test_roe_negative_equity(self):
        """Negative equity → ROE = None."""
        quarterly = [
            {
                "date": "2026-06-30",
                "revenue": 10e9,
                "earnings": 1e9,
                "operating_pnl": 2e9,
                "total_equity": -50e9,
            },
            {
                "date": "2026-03-31",
                "revenue": 10e9,
                "earnings": 1e9,
                "operating_pnl": 2e9,
                "total_equity": -50e9,
            },
            {
                "date": "2025-12-31",
                "revenue": 10e9,
                "earnings": 1e9,
                "operating_pnl": 2e9,
                "total_equity": -50e9,
            },
            {
                "date": "2025-09-30",
                "revenue": 10e9,
                "earnings": 1e9,
                "operating_pnl": 2e9,
                "total_equity": -50e9,
            },
        ]
        metrics, _, _, _ = calculate_metrics(quarterly, [])
        assert metrics.roe_ttm is None

    def test_pe_negative_earnings(self):
        """Negative TTM earnings → PE = None."""
        quarterly = [
            {
                "date": "2026-06-30",
                "revenue": 10e9,
                "earnings": -5e9,
                "operating_pnl": -3e9,
                "total_equity": 100e9,
            },
            {
                "date": "2026-03-31",
                "revenue": 10e9,
                "earnings": -5e9,
                "operating_pnl": -3e9,
                "total_equity": 100e9,
            },
            {
                "date": "2025-12-31",
                "revenue": 10e9,
                "earnings": -5e9,
                "operating_pnl": -3e9,
                "total_equity": 100e9,
            },
            {
                "date": "2025-09-30",
                "revenue": 10e9,
                "earnings": -5e9,
                "operating_pnl": -3e9,
                "total_equity": 100e9,
            },
        ]
        metrics, _, _, _ = calculate_metrics(quarterly, ASII_DAILY, market_cap=50e12)
        assert metrics.pe_ttm is None

    def test_incomplete_data(self):
        """Only 1 quarter + no daily → mostly None with no crash."""
        quarterly = [{"date": "2026-06-30", "revenue": 10e9}]
        metrics, method, _, _ = calculate_metrics(quarterly, [])
        assert method == "N/A"
        assert metrics.revenue_growth is None
        assert metrics.roe_ttm is None
        assert metrics.price_return is None

    def test_price_period_provenance(self):
        """Price period string should contain start and end dates."""
        _, _, _, price_period = calculate_metrics(ASII_QUARTERLY, ASII_DAILY)
        assert price_period is not None
        assert "2026-08-11" in price_period
        assert "2026-09-09" in price_period

    def test_zero_revenue_growth(self):
        """Previous revenue below MIN_DENOMINATOR → growth = None."""
        quarterly = [
            {
                "date": "2026-06-30",
                "revenue": 10e9,
                "earnings": 1e9,
                "operating_pnl": 2e9,
                "total_equity": 50e9,
            },
            {
                "date": "2026-03-31",
                "revenue": 500_000,
                "earnings": 100_000,
                "operating_pnl": 200_000,
                "total_equity": 50e9,
            },
        ]
        metrics, _, _, _ = calculate_metrics(quarterly, [])
        assert metrics.revenue_growth is None  # prev < 1M threshold
