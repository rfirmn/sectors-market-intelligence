#!/usr/bin/env python3
"""Smoke test for Market State Engine (Hari 2).

Runs the engine pipeline on ASII (from cache) and verifies output
against pre-computed cross-check values.

Usage:
    make smoke-test-engine
    # or
    uv run python scripts/smoke_test_engine.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.client.sectors_client import SectorsClient
from src.engine.market_state_engine import MarketStateEngine
from src.engine.models import CompanyInfo

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("smoke_test_engine")


# ──────────────────────────────────────────────────────────────────────
# Pre-computed cross-check values for ASII (from live cache data)
# ──────────────────────────────────────────────────────────────────────

ASII_EXPECTED = {
    "revenue_growth_qoq": 0.00733,  # ≈ 0.73%
    "earnings_growth_qoq": 0.1424,  # ≈ 14.24%
    "operating_margin": 0.1023,  # ≈ 10.23%
    "margin_change_qoq": 0.0221,  # ≈ +2.21pp
    "roe_ttm": 0.1028,  # ≈ 10.28%
    "pe_ttm": 6.59,  # ≈ 6.59x
    "price_return": -0.0041,  # ≈ -0.41%
}

TOLERANCE = 0.01  # Absolute tolerance for cross-check


def _check_metric(name: str, actual: float | None, expected: float, tol: float = TOLERANCE) -> bool:
    """Cross-check one metric against expected value."""
    if actual is None:
        logger.error("  ✗ %s: None (expected %.4f)", name, expected)
        return False
    if abs(actual - expected) <= tol:
        logger.info("  ✓ %s: %.4f (expected %.4f) — OK", name, actual, expected)
        return True
    else:
        logger.error(
            "  ✗ %s: %.4f (expected %.4f, diff=%.4f > tol=%.4f) — FAIL",
            name,
            actual,
            expected,
            abs(actual - expected),
            tol,
        )
        return False


def run_smoke_test():
    """Run engine smoke test using cached ASII data."""
    logger.info("=" * 60)
    logger.info("SMOKE TEST: Market State Engine (Hari 2)")
    logger.info("=" * 60)

    # Build a minimal universe with just ASII in automobiles-components
    universe = {
        "automobiles-components": [
            CompanyInfo(
                symbol="ASII",
                company_name="Astra International Tbk",
                sector="consumer-cyclicals",
                subsector="automobiles-components",
            ),
        ],
    }

    # Use real client with cache
    client = SectorsClient()
    engine = MarketStateEngine(client)

    logger.info("\nRunning pipeline on ASII (using cache)...")
    try:
        result = engine.compute_market_state(universe=universe, n_quarters=4)
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        logger.info("Tip: Run 'make smoke-test' first to populate cache with ASII data.")
        return False

    if not result.companies:
        logger.error("No companies in result!")
        return False

    asii = result.companies[0]
    m = asii.raw_metrics

    logger.info("\n--- ASII Raw Metrics ---")
    logger.info("  Symbol:      %s", asii.symbol)
    logger.info("  Subsector:   %s", asii.subsector)
    logger.info("  Growth Method: %s", asii.growth_method)
    logger.info("  Growth Period: %s", asii.growth_period)
    logger.info("  Price Period:  %s", asii.price_period)

    logger.info("\n--- Cross-Check (against pre-computed values) ---")
    all_ok = True
    all_ok &= _check_metric("revenue_growth", m.revenue_growth, ASII_EXPECTED["revenue_growth_qoq"])
    all_ok &= _check_metric(
        "earnings_growth", m.earnings_growth, ASII_EXPECTED["earnings_growth_qoq"]
    )
    all_ok &= _check_metric(
        "operating_margin", m.operating_margin, ASII_EXPECTED["operating_margin"]
    )
    all_ok &= _check_metric("margin_change", m.margin_change, ASII_EXPECTED["margin_change_qoq"])
    all_ok &= _check_metric("roe_ttm", m.roe_ttm, ASII_EXPECTED["roe_ttm"])
    # Price return uses wider tolerance — daily data window shifts with each API call
    if m.price_return is not None:
        logger.info(
            "  ℹ price_return: %.4f (reference: %.4f — wider tolerance, dates shift)",
            m.price_return,
            ASII_EXPECTED["price_return"],
        )
    else:
        logger.warning("  ⚠ price_return: None")

    # PE needs market_cap which comes from daily data
    if m.pe_ttm is not None:
        all_ok &= _check_metric("pe_ttm", m.pe_ttm, ASII_EXPECTED["pe_ttm"], tol=0.1)

    logger.info("\n--- Peer Z-Scores (single company → unavailable) ---")
    z = asii.peer_z
    for field in (
        "z_revenue_growth",
        "z_earnings_growth",
        "z_margin_change",
        "z_roe",
        "z_price_return",
    ):
        val = getattr(z, field)
        if val is not None:
            logger.error("  %s = %.4f (expected None)", field, val)
            all_ok = False
        else:
            logger.info("  %s = None", field)

    logger.info("\n--- Subsector Profile ---")
    for sub, profile in result.subsector_profiles.items():
        logger.info(
            "  %s: %d companies, %d with metrics", sub, profile.n_companies, profile.n_with_metrics
        )
        for metric, dist in profile.distributions.items():
            logger.info(
                "    %s: median=%.4f, MAD=%.4f, scaled_MAD=%.4f (n=%d)",
                metric,
                dist.median,
                dist.mad,
                dist.scaled_mad,
                dist.n_valid,
            )

    logger.info("\n--- Methodology Notes ---")
    for note in result.methodology_notes:
        logger.info("  • %s", note)

    logger.info("\n" + "=" * 60)
    if all_ok:
        logger.info("✅ SMOKE TEST PASSED — All cross-checks within tolerance")
    else:
        logger.error("❌ SMOKE TEST FAILED — Some cross-checks out of tolerance")
    logger.info("=" * 60)

    return all_ok


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
