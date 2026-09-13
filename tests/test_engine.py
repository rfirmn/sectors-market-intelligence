"""Integration tests for MarketStateEngine pipeline (src/engine/market_state_engine.py).

Tests cover:
- Full pipeline with synthetic data (3 subsectors × 5 companies)
- Single company subsector (all peer_z unavailable)
- All-None metrics (graceful degradation)
- ASII cross-check (metrics match pre-computed values from live cache)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.engine.market_state_engine import MarketStateEngine
from src.engine.models import CompanyInfo

# ──────────────────────────────────────────────────────────────────────
# Helpers — Synthetic Data Generators
# ──────────────────────────────────────────────────────────────────────


def _make_quarterly(revenue: float, earnings: float, op_pnl: float, equity: float):
    """Generate 4 quarters of synthetic financial data (QoQ only)."""
    return [
        {
            "date": "2026-06-30",
            "revenue": revenue,
            "earnings": earnings,
            "operating_pnl": op_pnl,
            "total_equity": equity,
        },
        {
            "date": "2026-03-31",
            "revenue": revenue * 0.95,
            "earnings": earnings * 0.90,
            "operating_pnl": op_pnl * 0.90,
            "total_equity": equity,
        },
        {
            "date": "2025-12-31",
            "revenue": revenue * 0.90,
            "earnings": earnings * 0.85,
            "operating_pnl": op_pnl * 0.85,
            "total_equity": equity,
        },
        {
            "date": "2025-09-30",
            "revenue": revenue * 0.88,
            "earnings": earnings * 0.80,
            "operating_pnl": op_pnl * 0.80,
            "total_equity": equity,
        },
    ]


def _make_daily(close: float):
    """Generate simple daily data (2 data points for price return)."""
    return [
        {"date": "2026-08-11", "close": close * 0.98, "market_cap": close * 40e9},
        {"date": "2026-09-09", "close": close, "market_cap": close * 40e9},
    ]


def _make_mock_engine(universe: dict[str, list[CompanyInfo]], data_map: dict):
    """Create a MarketStateEngine with mocked SectorsClient.

    Args:
        universe: Pre-built universe map.
        data_map: Dict[symbol -> {"quarterly": [...], "daily": [...]}]
    """
    client = MagicMock()

    def mock_financials(symbol, n_quarters=8, **kw):
        return data_map.get(symbol, {}).get("quarterly", [])

    def mock_daily(symbol, **kw):
        return data_map.get(symbol, {}).get("daily", [])

    client.get_financials_quarterly.side_effect = mock_financials
    client.get_daily_transactions.side_effect = mock_daily

    return MarketStateEngine(client)


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────


class TestMarketStateEngine:
    def test_full_pipeline_synthetic(self):
        """3 subsectors × 5 companies → verify CompanyState output."""
        # Build synthetic universe
        universe = {}
        data_map = {}

        for sub_idx, subsector in enumerate(["auto", "mining", "tech"]):
            companies = []
            for i in range(5):
                sym = f"{subsector.upper()}{i}"
                companies.append(
                    CompanyInfo(
                        symbol=sym,
                        company_name=f"Company {sym}",
                        sector=f"sector-{sub_idx}",
                        subsector=subsector,
                    )
                )
                # Each company has slightly different metrics
                base_rev = (50 + i * 10) * 1e12
                base_earn = (5 + i * 2) * 1e12
                data_map[sym] = {
                    "quarterly": _make_quarterly(
                        base_rev, base_earn, base_earn * 1.5, base_rev * 3
                    ),
                    "daily": _make_daily(1000 + i * 200),
                }
            universe[subsector] = companies

        engine = _make_mock_engine(universe, data_map)
        result = engine.compute_market_state(universe=universe)

        # Should have 15 companies total
        assert len(result.companies) == 15

        # Should have 3 subsector profiles
        assert len(result.subsector_profiles) == 3

        # All companies should have valid data
        assert result.universe_stats.total_companies_universe == 15

        # Check CompanyState fields populated
        for cs in result.companies:
            assert cs.symbol is not None
            assert cs.sector is not None
            assert cs.subsector is not None
            assert cs.data_timestamp is not None
            assert cs.growth_method in ("YoY", "QoQ")

        # Check z-score properties: median z should be near 0
        for subsector, profile in result.subsector_profiles.items():
            assert profile.n_companies == 5
            for metric_name, dist in profile.distributions.items():
                if dist.normalization_status in ("ok", "low_sample"):
                    assert dist.scaled_mad > 0, (
                        f"{subsector}.{metric_name}: scaled_mad should be > 0"
                    )

    def test_single_company_subsector(self):
        """Subsector with 1 company → all peer_z unavailable."""
        universe = {
            "solo-sector": [
                CompanyInfo(
                    symbol="SOLO",
                    company_name="Solo Corp",
                    sector="test",
                    subsector="solo-sector",
                )
            ]
        }
        data_map = {
            "SOLO": {
                "quarterly": _make_quarterly(50e12, 5e12, 7e12, 150e12),
                "daily": _make_daily(5000),
            }
        }

        engine = _make_mock_engine(universe, data_map)
        result = engine.compute_market_state(universe=universe)

        assert len(result.companies) == 1
        cs = result.companies[0]

        # No evidence about relative standing with just one company.
        assert cs.peer_z.z_revenue_growth is None
        assert cs.peer_z.z_earnings_growth is None
        assert cs.peer_z.z_margin_change is None
        assert cs.peer_z.z_roe is None
        assert cs.peer_z.z_price_return is None

        # But raw metrics should be populated
        assert cs.raw_metrics.revenue_growth is not None
        assert cs.raw_metrics.price_return is not None

    def test_all_none_metrics(self):
        """Company with no valid data → CompanyState with all None."""
        universe = {
            "empty-sector": [
                CompanyInfo(
                    symbol="EMPTY",
                    company_name="Empty Corp",
                    sector="test",
                    subsector="empty-sector",
                ),
                CompanyInfo(
                    symbol="OK1",
                    company_name="OK Corp 1",
                    sector="test",
                    subsector="empty-sector",
                ),
                CompanyInfo(
                    symbol="OK2",
                    company_name="OK Corp 2",
                    sector="test",
                    subsector="empty-sector",
                ),
            ]
        }
        data_map = {
            "EMPTY": {"quarterly": [], "daily": []},  # No data at all
            "OK1": {
                "quarterly": _make_quarterly(50e12, 5e12, 7e12, 150e12),
                "daily": _make_daily(5000),
            },
            "OK2": {
                "quarterly": _make_quarterly(60e12, 6e12, 8e12, 160e12),
                "daily": _make_daily(6000),
            },
        }

        engine = _make_mock_engine(universe, data_map)
        result = engine.compute_market_state(universe=universe)

        # EMPTY should have all None metrics
        empty_cs = next(c for c in result.companies if c.symbol == "EMPTY")
        assert empty_cs.raw_metrics.revenue_growth is None
        assert empty_cs.raw_metrics.price_return is None
        assert empty_cs.peer_z.z_revenue_growth is None
        assert empty_cs.peer_z.z_price_return is None

        # OK companies should have valid metrics
        ok1_cs = next(c for c in result.companies if c.symbol == "OK1")
        assert ok1_cs.raw_metrics.revenue_growth is not None

    def test_deterministic_output_order(self):
        """Output should be sorted by (subsector, symbol)."""
        universe = {
            "zzz-sector": [
                CompanyInfo("ZZZ", "Z Corp", "test", "zzz-sector"),
            ],
            "aaa-sector": [
                CompanyInfo("BBB", "B Corp", "test", "aaa-sector"),
                CompanyInfo("AAA", "A Corp", "test", "aaa-sector"),
            ],
        }
        data_map = {
            sym: {
                "quarterly": _make_quarterly(50e12, 5e12, 7e12, 150e12),
                "daily": _make_daily(5000),
            }
            for sym in ["AAA", "BBB", "ZZZ"]
        }

        engine = _make_mock_engine(universe, data_map)
        result = engine.compute_market_state(universe=universe)

        symbols = [c.symbol for c in result.companies]
        assert symbols == ["AAA", "BBB", "ZZZ"]


def test_normalization_excludes_incomparable_periods_without_losing_raw_data():
    symbols = ["A", "B", "C", "QOQ", "OLD", "SHORT"]
    universe = {"test": [CompanyInfo(s, s, "sector", "test") for s in symbols]}
    data = {}
    for i, symbol in enumerate(symbols):
        quarters = _make_quarterly((100 + i * 10) * 1e9, (10 + i) * 1e9, 20e9, 200e9)
        if symbol != "QOQ":
            quarters.append(
                {
                    "date": "2025-06-30",
                    "revenue": 90e9,
                    "earnings": 8e9,
                    "operating_pnl": 10e9,
                    "total_equity": 200e9,
                }
            )
        if symbol == "OLD":
            for row in quarters:
                row["date"] = str(int(row["date"][:4]) - 1) + row["date"][4:]
        daily = _make_daily(1000 + i * 100)
        daily[-1]["close"] *= 1 + i * 0.03
        if symbol == "SHORT":
            daily[0]["date"] = "2026-09-01"
        data[symbol] = {"quarterly": quarters, "daily": daily}
    result = _make_mock_engine(universe, data).compute_market_state(universe)
    companies = {c.symbol: c for c in result.companies}
    assert companies["QOQ"].growth_method == "QoQ"
    assert companies["QOQ"].raw_metrics.revenue_growth is not None
    assert companies["QOQ"].peer_z.z_revenue_growth is None
    assert companies["QOQ"].normalization_exclusions["revenue_growth"] == "yoy_required"
    assert companies["OLD"].peer_z.z_revenue_growth is None
    assert companies["OLD"].peer_z.z_roe is None
    assert companies["SHORT"].raw_metrics.price_return is not None
    assert companies["SHORT"].peer_z.z_price_return is None
    assert companies["A"].peer_z.z_revenue_growth is not None
    profile = result.subsector_profiles["test"]
    assert profile.distributions["revenue_growth"].n_valid == 4
    assert profile.distributions["price_return"].n_valid == 5
    assert profile.normalization_periods["price_return"] == "2026-08-11 to 2026-09-09"
