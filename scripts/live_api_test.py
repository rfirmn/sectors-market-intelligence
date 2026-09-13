#!/usr/bin/env python3
"""Live API Integration Test — Market State Engine v2 (validity-v2).

Simulates real-world usage of the Market State Engine with live Sectors API data.
Tests two primary user personas:

1. PROFESSIONAL INVESTOR — Multi-company subsector scans with real peer groups,
   evaluates peer normalization quality, checks discrepancy signals.
2. BEGINNER INVESTOR — Single-stock analysis, checks whether output is
   understandable, complete, and non-misleading.

This script calls the live Sectors API (with cache fallback). Results are saved
to data/test_results/ for documentation.

Usage:
    uv run python scripts/live_api_test.py
    uv run python scripts/live_api_test.py --professional-only
    uv run python scripts/live_api_test.py --beginner-only
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.client.sectors_client import SectorsClient
from src.engine.market_state_engine import MarketStateEngine
from src.engine.models import CompanyInfo, CompanyState, MarketStateResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("live_api_test")

# ──────────────────────────────────────────────────────────────────────
# Output directory
# ──────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "test_results"

# ──────────────────────────────────────────────────────────────────────
# Test result data structures
# ──────────────────────────────────────────────────────────────────────


@dataclass
class MetricQualityCheck:
    """Quality evaluation for a single metric."""

    metric: str
    value: float | None
    has_value: bool
    is_reasonable: bool
    reason: str = ""


@dataclass
class CompanyTestResult:
    """Test result for a single company."""

    symbol: str
    company_name: str | None
    subsector: str
    sector: str
    growth_method: str | None
    growth_period: str | None
    price_period: str | None
    metric_checks: list[MetricQualityCheck] = field(default_factory=list)
    z_score_checks: list[MetricQualityCheck] = field(default_factory=list)
    data_completeness: float = 0.0
    has_normalization_exclusions: bool = False
    exclusion_reasons: dict[str, str] = field(default_factory=dict)
    verdict: str = ""


@dataclass
class SubsectorTestResult:
    """Test result for a subsector peer group."""

    subsector: str
    sector: str
    n_companies: int
    n_with_metrics: int
    companies: list[CompanyTestResult] = field(default_factory=list)
    distribution_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    peer_normalization_working: bool = False
    verdict: str = ""


@dataclass
class ScenarioResult:
    """Full test scenario result."""

    scenario: str
    description: str
    timestamp: str
    duration_seconds: float = 0.0
    subsectors_tested: int = 0
    companies_tested: int = 0
    subsector_results: list[SubsectorTestResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_verdict: str = ""
    quality_summary: dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────
# Known IDX universe — Professional investor's watchlist
# ──────────────────────────────────────────────────────────────────────

# Real IDX companies grouped by subsector, selected for peer diversity.
# A professional investor would know these groupings.
PROFESSIONAL_UNIVERSE: dict[str, list[tuple[str, str, str]]] = {
    # (symbol, company_name, sector)
    "automobiles-components": [
        ("ASII", "Astra International", "consumer-cyclicals"),
        ("AUTO", "Astra Otoparts", "consumer-cyclicals"),
        ("IMAS", "Indomobil Sukses Internasional", "consumer-cyclicals"),
        ("SMSM", "Selamat Sempurna", "consumer-cyclicals"),
        ("BOLT", "Garuda Metalindo", "consumer-cyclicals"),
    ],
    "food-beverage": [
        ("ICBP", "Indofood CBP Sukses Makmur", "consumer-non-cyclicals"),
        ("INDF", "Indofood Sukses Makmur", "consumer-non-cyclicals"),
        ("MYOR", "Mayora Indah", "consumer-non-cyclicals"),
        ("CLEO", "Sariguna Primatirta", "consumer-non-cyclicals"),
        ("ULTJ", "Ultra Jaya Milk Industry", "consumer-non-cyclicals"),
        ("GOOD", "Garudafood Putra Putri Jaya", "consumer-non-cyclicals"),
    ],
    "oil-gas-coal": [
        ("ADRO", "Adaro Energy Indonesia", "energy"),
        ("PTBA", "Bukit Asam", "energy"),
        ("ITMG", "Indo Tambangraya Megah", "energy"),
        ("INDY", "Indika Energy", "energy"),
        ("MEDC", "Medco Energi Internasional", "energy"),
    ],
    "telecommunication": [
        ("TLKM", "Telkom Indonesia", "infrastructures"),
        ("EXCL", "XL Axiata", "infrastructures"),
        ("ISAT", "Indosat Ooredoo Hutchison", "infrastructures"),
        ("TOWR", "Sarana Menara Nusantara", "infrastructures"),
        ("TBIG", "Tower Bersama Infrastructure", "infrastructures"),
    ],
    "properties-real-estate": [
        ("BSDE", "Bumi Serpong Damai", "properties-real-estate"),
        ("CTRA", "Ciputra Development", "properties-real-estate"),
        ("SMRA", "Summarecon Agung", "properties-real-estate"),
        ("PWON", "Pakuwon Jati", "properties-real-estate"),
        ("LPKR", "Lippo Karawaci", "properties-real-estate"),
    ],
}

# Beginner stocks
BEGINNER_STOCKS = [
    ("ASII", "Astra International", "consumer-cyclicals", "automobiles-components"),
    ("TLKM", "Telkom Indonesia", "infrastructures", "telecommunication"),
    ("UNVR", "Unilever Indonesia", "consumer-non-cyclicals", "nondurable-household-products"),
    ("BBCA", "Bank Central Asia", "financials", "banks"),  # Financial — should be excluded
    ("ICBP", "Indofood CBP", "consumer-non-cyclicals", "food-beverage"),
    ("GOTO", "GoTo Gojek Tokopedia", "technology", "software-it-services"),
]


# ──────────────────────────────────────────────────────────────────────
# Quality evaluation functions
# ──────────────────────────────────────────────────────────────────────

METRIC_RANGES = {
    "revenue_growth": (-1.0, 10.0),
    "earnings_growth": (-5.0, 50.0),
    "operating_margin": (-1.0, 1.0),
    "margin_change": (-1.0, 1.0),
    "roe_ttm": (-2.0, 2.0),
    "price_return": (-0.9, 5.0),
    "pe_ttm": (0.0, 500.0),
    "pb": (0.0, 100.0),
}

Z_SCORE_RANGE = (-20.0, 20.0)


def check_metric_quality(name: str, value: float | None) -> MetricQualityCheck:
    """Evaluate whether a single metric value is reasonable."""
    if value is None:
        return MetricQualityCheck(
            metric=name, value=None, has_value=False,
            is_reasonable=True, reason="unavailable (valid per data contract)"
        )
    lo, hi = METRIC_RANGES.get(name, (-1e10, 1e10))
    is_reasonable = lo <= value <= hi
    reason = f"outside plausible range [{lo}, {hi}]: {value:.6f}" if not is_reasonable else f"within range [{lo}, {hi}]"
    return MetricQualityCheck(metric=name, value=value, has_value=True, is_reasonable=is_reasonable, reason=reason)


def check_zscore_quality(name: str, value: float | None) -> MetricQualityCheck:
    """Evaluate whether a z-score is within reasonable bounds."""
    if value is None:
        return MetricQualityCheck(
            metric=name, value=None, has_value=False,
            is_reasonable=True, reason="unavailable (insufficient peers or degenerate scale)"
        )
    lo, hi = Z_SCORE_RANGE
    is_reasonable = lo <= value <= hi
    reason = f"extreme z-score {value:.4f}" if not is_reasonable else f"z={value:.4f}"
    return MetricQualityCheck(metric=name, value=value, has_value=True, is_reasonable=is_reasonable, reason=reason)


def evaluate_company(cs: CompanyState) -> CompanyTestResult:
    """Run all quality checks on a single CompanyState."""
    m = cs.raw_metrics
    z = cs.peer_z

    metric_checks = [
        check_metric_quality("revenue_growth", m.revenue_growth),
        check_metric_quality("earnings_growth", m.earnings_growth),
        check_metric_quality("operating_margin", m.operating_margin),
        check_metric_quality("margin_change", m.margin_change),
        check_metric_quality("roe_ttm", m.roe_ttm),
        check_metric_quality("price_return", m.price_return),
        check_metric_quality("pe_ttm", m.pe_ttm),
        check_metric_quality("pb", m.pb),
    ]

    z_checks = [
        check_zscore_quality("z_revenue_growth", z.z_revenue_growth),
        check_zscore_quality("z_earnings_growth", z.z_earnings_growth),
        check_zscore_quality("z_margin_change", z.z_margin_change),
        check_zscore_quality("z_roe", z.z_roe),
        check_zscore_quality("z_price_return", z.z_price_return),
    ]

    raw_fields = [m.revenue_growth, m.earnings_growth, m.operating_margin,
                  m.margin_change, m.roe_ttm, m.price_return]
    n_available = sum(1 for f in raw_fields if f is not None)
    completeness = n_available / len(raw_fields)

    all_reasonable = all(c.is_reasonable for c in metric_checks + z_checks)
    if all_reasonable and completeness >= 0.5:
        verdict = "GOOD — data complete and reasonable"
    elif all_reasonable:
        verdict = f"PARTIAL — reasonable but only {completeness:.0%} complete"
    else:
        bad_metrics = [c.metric for c in metric_checks + z_checks if not c.is_reasonable]
        verdict = f"WARNING — outlier values in: {', '.join(bad_metrics)}"

    return CompanyTestResult(
        symbol=cs.symbol, company_name=cs.company_name,
        subsector=cs.subsector, sector=cs.sector,
        growth_method=cs.growth_method, growth_period=cs.growth_period,
        price_period=cs.price_period,
        metric_checks=metric_checks, z_score_checks=z_checks,
        data_completeness=completeness,
        has_normalization_exclusions=bool(cs.normalization_exclusions),
        exclusion_reasons=cs.normalization_exclusions,
        verdict=verdict,
    )


def evaluate_subsector(
    subsector: str, companies: list[CompanyState], result: MarketStateResult
) -> SubsectorTestResult:
    """Evaluate all companies in a subsector and assess peer normalization quality."""
    profile = result.subsector_profiles.get(subsector)
    company_results = [evaluate_company(cs) for cs in companies]

    dist_checks: dict[str, dict[str, Any]] = {}
    if profile:
        for metric_name, dist in profile.distributions.items():
            dist_checks[metric_name] = {
                "n_valid": dist.n_valid,
                "median": round(dist.median, 6),
                "mad": round(dist.mad, 6),
                "scaled_mad": round(dist.scaled_mad, 6),
                "status": dist.normalization_status,
                "was_winsorized": dist.was_winsorized,
            }

    # Check if peer normalization is working
    all_z_values: dict[str, list[float]] = {}
    for cs in companies:
        for zf in ("z_revenue_growth", "z_earnings_growth", "z_margin_change",
                    "z_roe", "z_price_return"):
            val = getattr(cs.peer_z, zf)
            if val is not None:
                all_z_values.setdefault(zf, []).append(val)

    normalization_working = any(
        len(vals) >= 2 and (max(vals) - min(vals)) > 0.01
        for vals in all_z_values.values()
    )

    good_count = sum(1 for c in company_results if "GOOD" in c.verdict)
    total = len(company_results)

    if normalization_working and good_count >= total * 0.5:
        verdict = f"GOOD — normalization working, {good_count}/{total} companies good"
    elif normalization_working:
        verdict = f"PARTIAL — normalization working, {good_count}/{total} companies good"
    elif total <= 2:
        verdict = f"SMALL — only {total} companies, limited peer normalization"
    else:
        verdict = f"WEAK — normalization not producing spread, {good_count}/{total} good"

    return SubsectorTestResult(
        subsector=subsector,
        sector=profile.sector if profile else "",
        n_companies=profile.n_companies if profile else len(companies),
        n_with_metrics=profile.n_with_metrics if profile else 0,
        companies=company_results,
        distribution_checks=dist_checks,
        peer_normalization_working=normalization_working,
        verdict=verdict,
    )


# ──────────────────────────────────────────────────────────────────────
# Professional Scenario
# ──────────────────────────────────────────────────────────────────────


def run_professional_scenario(client: SectorsClient) -> ScenarioResult:
    """Simulate a professional investor scanning multiple subsectors.

    Professional workflow:
    1. Scan known peer groups for fundamental vs price discrepancy
    2. Compare z-scores within each peer group
    3. Check methodology transparency and data provenance
    4. Identify discrepancy candidates (high F-score, low price)
    """
    logger.info("=" * 70)
    logger.info("SCENARIO 1: PROFESSIONAL INVESTOR — Multi-Subsector Peer Scan")
    logger.info("=" * 70)

    start_time = time.time()
    engine = MarketStateEngine(client)

    # Build universe from hardcoded professional watchlist
    universe: dict[str, list[CompanyInfo]] = {}
    for subsector, stocks in PROFESSIONAL_UNIVERSE.items():
        universe[subsector] = [
            CompanyInfo(symbol=sym, company_name=name, sector=sector, subsector=subsector)
            for sym, name, sector in stocks
        ]
        logger.info("  Universe: %s → %d companies", subsector, len(stocks))

    total_in_universe = sum(len(v) for v in universe.values())
    logger.info("  Total universe: %d companies in %d subsectors", total_in_universe, len(universe))

    # Run the engine pipeline
    logger.info("\nRunning full engine pipeline (n_quarters=8 for YoY)...")
    try:
        result = engine.compute_market_state(universe=universe, n_quarters=8)
    except Exception as e:
        logger.error("Engine pipeline failed: %s", e)
        return ScenarioResult(
            scenario="professional",
            description=f"Pipeline failed: {e}",
            timestamp=datetime.now(UTC).isoformat(),
            overall_verdict=f"FAIL — {e}",
        )

    # Evaluate results
    subsector_results: list[SubsectorTestResult] = []
    companies_by_sub: dict[str, list[CompanyState]] = {}
    for cs in result.companies:
        companies_by_sub.setdefault(cs.subsector, []).append(cs)

    for sub, cos in companies_by_sub.items():
        sr = evaluate_subsector(sub, cos, result)
        subsector_results.append(sr)
        _print_professional_subsector(sub, cos, result, sr)

    # Print discrepancy analysis (what a professional would look for)
    _print_discrepancy_analysis(result)

    # Score
    duration = time.time() - start_time
    total_companies = sum(len(sr.companies) for sr in subsector_results)
    good_subs = sum(1 for sr in subsector_results if "GOOD" in sr.verdict)
    norm_working = sum(1 for sr in subsector_results if sr.peer_normalization_working)

    all_completeness = []
    all_reasonable = 0
    all_total_checks = 0
    for sr in subsector_results:
        for cr in sr.companies:
            all_completeness.append(cr.data_completeness)
            for mc in cr.metric_checks + cr.z_score_checks:
                all_total_checks += 1
                if mc.is_reasonable:
                    all_reasonable += 1

    avg_completeness = sum(all_completeness) / len(all_completeness) if all_completeness else 0
    reasonability_rate = all_reasonable / all_total_checks if all_total_checks else 0

    score = (
        0.30 * (good_subs / len(subsector_results) if subsector_results else 0)
        + 0.25 * (norm_working / len(subsector_results) if subsector_results else 0)
        + 0.25 * reasonability_rate
        + 0.20 * avg_completeness
    ) * 100

    if score >= 70:
        verdict = f"PASS — Score {score:.1f}/100"
    elif score >= 50:
        verdict = f"MARGINAL — Score {score:.1f}/100"
    else:
        verdict = f"FAIL — Score {score:.1f}/100"

    quality_summary = {
        "subsectors_good": f"{good_subs}/{len(subsector_results)}",
        "normalization_working": f"{norm_working}/{len(subsector_results)}",
        "avg_data_completeness": f"{avg_completeness:.1%}",
        "metric_reasonability": f"{reasonability_rate:.1%}",
        "total_metric_checks": all_total_checks,
        "methodology_version": "2026-09-13-validity-v2",
        "methodology_notes_count": len(result.methodology_notes),
    }

    return ScenarioResult(
        scenario="professional",
        description="Multi-subsector peer analysis with real API data",
        timestamp=datetime.now(UTC).isoformat(),
        duration_seconds=round(duration, 2),
        subsectors_tested=len(subsector_results),
        companies_tested=total_companies,
        subsector_results=subsector_results,
        overall_score=round(score, 1),
        overall_verdict=verdict,
        quality_summary=quality_summary,
    )


def _print_professional_subsector(
    subsector: str,
    companies: list[CompanyState],
    result: MarketStateResult,
    sr: SubsectorTestResult,
) -> None:
    """Print professional-grade subsector analysis."""
    profile = result.subsector_profiles.get(subsector)
    logger.info("\n┌─────────────────────────────────────────────────────────────")
    logger.info("│ 📊 SUBSECTOR: %s", subsector)
    if profile:
        logger.info("│ Companies: %d total, %d with metrics", profile.n_companies, profile.n_with_metrics)
        if profile.normalization_periods:
            logger.info("│ Cohort periods: %s", profile.normalization_periods)
    logger.info("│")

    # Distribution summary
    if profile:
        logger.info("│ Distribution Statistics:")
        logger.info("│ %-20s %10s %10s %10s %6s %s", "Metric", "Median", "MAD", "ScaledMAD", "N", "Status")
        logger.info("│ " + "─" * 70)
        for metric_name, dist in profile.distributions.items():
            logger.info(
                "│ %-20s %10.4f %10.4f %10.4f %6d %s",
                metric_name, dist.median, dist.mad, dist.scaled_mad, dist.n_valid, dist.normalization_status
            )

    # Company results table
    logger.info("│")
    logger.info("│ Company Results:")
    logger.info("│ %-6s %-18s %10s %10s %10s %10s %10s %10s",
                "Sym", "Growth", "RevGr", "EarnGr", "MargΔ", "ROE", "PriceR", "Complete")
    logger.info("│ " + "─" * 90)

    for cs in companies:
        m = cs.raw_metrics
        z = cs.peer_z
        gm = cs.growth_method or "N/A"
        logger.info(
            "│ %-6s %-18s %10s %10s %10s %10s %10s %10s",
            cs.symbol,
            f"{gm} {(cs.growth_period or '')[:15]}",
            _fmt_pct(m.revenue_growth),
            _fmt_pct(m.earnings_growth),
            _fmt_pp(m.margin_change),
            _fmt_pct(m.roe_ttm),
            _fmt_pct(m.price_return),
            f"{'█' * int(sum(1 for f in [m.revenue_growth, m.earnings_growth, m.margin_change, m.roe_ttm, m.price_return] if f is not None) / 5 * 5)}{'░' * (5 - int(sum(1 for f in [m.revenue_growth, m.earnings_growth, m.margin_change, m.roe_ttm, m.price_return] if f is not None) / 5 * 5))}",
        )

    # Z-score table
    any_z = any(
        getattr(cs.peer_z, zf) is not None
        for cs in companies
        for zf in ("z_revenue_growth", "z_earnings_growth", "z_margin_change", "z_roe", "z_price_return")
    )
    if any_z:
        logger.info("│")
        logger.info("│ Peer Z-Scores:")
        logger.info("│ %-6s %10s %10s %10s %10s %10s", "Sym", "zRevGr", "zEarnGr", "zMargΔ", "zROE", "zPriceR")
        logger.info("│ " + "─" * 60)
        for cs in companies:
            z = cs.peer_z
            logger.info(
                "│ %-6s %10s %10s %10s %10s %10s",
                cs.symbol,
                _fmt_z(z.z_revenue_growth),
                _fmt_z(z.z_earnings_growth),
                _fmt_z(z.z_margin_change),
                _fmt_z(z.z_roe),
                _fmt_z(z.z_price_return),
            )

    # Exclusions
    has_exclusions = any(cs.normalization_exclusions for cs in companies)
    if has_exclusions:
        logger.info("│")
        logger.info("│ Normalization Exclusions:")
        for cs in companies:
            if cs.normalization_exclusions:
                logger.info("│   %s: %s", cs.symbol, cs.normalization_exclusions)

    logger.info("│")
    logger.info("│ Verdict: %s", sr.verdict)
    logger.info("└─────────────────────────────────────────────────────────────")


def _print_discrepancy_analysis(result: MarketStateResult) -> None:
    """Compute and print discrepancy scores — the core output of the engine."""
    logger.info("\n╔═══════════════════════════════════════════════════════════════╗")
    logger.info("║  📈 DISCREPANCY ANALYSIS — D = F - z_price_return          ║")
    logger.info("║  F = (z_rev + z_earn + z_marg) / 3                         ║")
    logger.info("║  Candidate: D > 1.0 | HIGH: D > 1.5                       ║")
    logger.info("╚═══════════════════════════════════════════════════════════════╝")

    candidates = []
    for cs in result.companies:
        z = cs.peer_z
        z_rev = z.z_revenue_growth
        z_earn = z.z_earnings_growth
        z_marg = z.z_margin_change
        z_price = z.z_price_return

        # All three growth z-scores AND price z required
        if any(v is None for v in (z_rev, z_earn, z_marg, z_price)):
            continue

        f_score = (z_rev + z_earn + z_marg) / 3
        d_score = f_score - z_price

        candidates.append({
            "symbol": cs.symbol,
            "subsector": cs.subsector,
            "F": f_score,
            "z_price": z_price,
            "D": d_score,
            "label": "HIGH" if d_score > 1.5 else "CANDIDATE" if d_score > 1.0 else "—",
            "growth_method": cs.growth_method,
        })

    if not candidates:
        logger.info("\n  No companies with complete z-scores for discrepancy computation.")
        logger.info("  This is expected when peer groups have <3 members with YoY data.")
        return

    candidates.sort(key=lambda x: x["D"], reverse=True)

    logger.info("\n%-6s %-28s %8s %8s %8s %10s %s",
                "Sym", "Subsector", "F", "zPrice", "D", "Label", "Method")
    logger.info("─" * 80)

    for c in candidates:
        label_icon = "🔴" if c["label"] == "HIGH" else "🟡" if c["label"] == "CANDIDATE" else "  "
        logger.info(
            "%-6s %-28s %8.3f %8.3f %8.3f %s %-10s %s",
            c["symbol"], c["subsector"], c["F"], c["z_price"], c["D"],
            label_icon, c["label"], c["growth_method"],
        )

    n_high = sum(1 for c in candidates if c["label"] == "HIGH")
    n_cand = sum(1 for c in candidates if c["label"] == "CANDIDATE")
    logger.info("\nSummary: %d HIGH, %d CANDIDATE, %d total with complete data",
                n_high, n_cand, len(candidates))


# ──────────────────────────────────────────────────────────────────────
# Beginner Scenario
# ──────────────────────────────────────────────────────────────────────


def run_beginner_scenario(client: SectorsClient) -> ScenarioResult:
    """Simulate a beginner investor looking at individual stocks."""
    logger.info("\n" + "=" * 70)
    logger.info("SCENARIO 2: BEGINNER INVESTOR — Individual Stock Lookup")
    logger.info("=" * 70)

    start_time = time.time()
    engine = MarketStateEngine(client)
    subsector_results: list[SubsectorTestResult] = []
    companies_tested = 0

    for sym, name, sector, subsector in BEGINNER_STOCKS:
        logger.info("\n--- Beginner looks up: %s (%s) ---", sym, name)

        if sector == "financials":
            logger.info("  ⚠ %s is financial-sector — excluded from universe by design", sym)
            universe = {subsector: [CompanyInfo(symbol=sym, company_name=name, sector=sector, subsector=subsector)]}
            try:
                result = engine.compute_market_state(universe=universe, n_quarters=8)
                if result.companies:
                    cs = result.companies[0]
                    cr = evaluate_company(cs)
                    sr = SubsectorTestResult(
                        subsector=subsector, sector=sector, n_companies=1,
                        n_with_metrics=1 if cr.data_completeness > 0 else 0,
                        companies=[cr],
                        verdict="NOTE — Financial stock processed (should be filtered at universe level)"
                    )
                    subsector_results.append(sr)
                    companies_tested += 1
                    _print_beginner_output(cs, result)
            except Exception as e:
                logger.info("  Pipeline correctly rejected financial stock: %s", e)
            continue

        universe = {subsector: [CompanyInfo(symbol=sym, company_name=name, sector=sector, subsector=subsector)]}

        try:
            result = engine.compute_market_state(universe=universe, n_quarters=8)
        except Exception as e:
            logger.warning("  Failed for %s: %s", sym, e)
            subsector_results.append(SubsectorTestResult(
                subsector=subsector, sector=sector, n_companies=1, n_with_metrics=0,
                verdict=f"FAIL — {e}",
            ))
            continue

        if not result.companies:
            subsector_results.append(SubsectorTestResult(
                subsector=subsector, sector=sector, n_companies=1, n_with_metrics=0,
                verdict="FAIL — no output",
            ))
            continue

        cs = result.companies[0]
        cr = evaluate_company(cs)
        companies_tested += 1

        # Beginner-specific checks
        beginner_issues = []

        z_fields = [cs.peer_z.z_revenue_growth, cs.peer_z.z_earnings_growth,
                     cs.peer_z.z_margin_change, cs.peer_z.z_roe, cs.peer_z.z_price_return]
        if all(z is None for z in z_fields):
            logger.info("  ✓ Z-scores correctly None for single-company lookup")
        elif any(z is not None for z in z_fields):
            beginner_issues.append("Z-scores available for single company — unexpected")

        if not cs.growth_period:
            beginner_issues.append("No growth period — beginner can't verify timeframe")

        if result.methodology_notes:
            logger.info("  ✓ Methodology notes present (%d notes)", len(result.methodology_notes))
        else:
            beginner_issues.append("No methodology notes")

        if cs.raw_metrics.revenue_growth is None and cs.raw_metrics.earnings_growth is None:
            beginner_issues.append("No growth data — empty analysis for beginner")

        if beginner_issues:
            verdict = f"ISSUES for beginner: {'; '.join(beginner_issues)}"
        else:
            verdict = "GOOD — single stock analysis clear and honest"

        sr = SubsectorTestResult(
            subsector=subsector, sector=sector, n_companies=1,
            n_with_metrics=1 if cr.data_completeness > 0 else 0,
            companies=[cr], verdict=verdict,
        )
        subsector_results.append(sr)
        _print_beginner_output(cs, result)

    duration = time.time() - start_time
    good_count = sum(1 for sr in subsector_results if "GOOD" in sr.verdict)
    total = len(subsector_results)
    score = (good_count / total * 100) if total else 0

    if score >= 60:
        verdict = f"PASS — {good_count}/{total} stocks produced good beginner output"
    else:
        verdict = f"NEEDS WORK — only {good_count}/{total} stocks good for beginners"

    return ScenarioResult(
        scenario="beginner",
        description="Individual stock lookup with beginner-friendly evaluation",
        timestamp=datetime.now(UTC).isoformat(),
        duration_seconds=round(duration, 2),
        subsectors_tested=total,
        companies_tested=companies_tested,
        subsector_results=subsector_results,
        overall_score=round(score, 1),
        overall_verdict=verdict,
        quality_summary={
            "stocks_tested": [s[0] for s in BEGINNER_STOCKS],
            "good_outputs": good_count,
            "total_tested": total,
            "financial_sector_tested": True,
        },
    )


def _print_beginner_output(cs: CompanyState, result: MarketStateResult) -> None:
    """Print a beginner-friendly summary."""
    m = cs.raw_metrics
    logger.info("  ┌──────────────────────────────────────────────────")
    logger.info("  │ 📊 %s — %s", cs.symbol, cs.company_name or "N/A")
    logger.info("  │ Sektor: %s | Subsektor: %s", cs.sector, cs.subsector)
    logger.info("  │")
    if cs.growth_period:
        logger.info("  │ 📅 Periode growth: %s (%s)", cs.growth_period, cs.growth_method)
    if cs.price_period:
        logger.info("  │ 📅 Periode harga: %s", cs.price_period)
    logger.info("  │")
    logger.info("  │ 📈 Metrik Fundamental:")
    _log_metric("  │   Revenue Growth", m.revenue_growth, is_pct=True)
    _log_metric("  │   Earnings Growth", m.earnings_growth, is_pct=True)
    _log_metric("  │   Operating Margin", m.operating_margin, is_pct=True)
    _log_metric("  │   Margin Change", m.margin_change, is_pct=True, suffix="pp")
    _log_metric("  │   ROE (TTM)", m.roe_ttm, is_pct=True)
    _log_metric("  │   PE (TTM)", m.pe_ttm, suffix="x")
    _log_metric("  │   PB", m.pb, suffix="x")
    logger.info("  │")
    logger.info("  │ 📉 Pergerakan Harga:")
    _log_metric("  │   Price Return", m.price_return, is_pct=True)
    logger.info("  │")
    logger.info("  │ 🔍 Status Peer Z-Score: semua None = wajar untuk analisis saham tunggal")
    logger.info("  └──────────────────────────────────────────────────")


def _log_metric(label: str, value: float | None, is_pct: bool = False, suffix: str = "") -> None:
    if value is None:
        logger.info("%s: — (data tidak tersedia)", label)
    elif is_pct:
        logger.info("%s: %.2f%% %s", label, value * 100, suffix)
    else:
        logger.info("%s: %.2f %s", label, value, suffix)


def _fmt_pct(v: float | None) -> str:
    return f"{v*100:.2f}%" if v is not None else "—"

def _fmt_pp(v: float | None) -> str:
    return f"{v*100:+.2f}pp" if v is not None else "—"

def _fmt_z(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "—"


# ──────────────────────────────────────────────────────────────────────
# Summary and serialization
# ──────────────────────────────────────────────────────────────────────


def print_scenario_summary(sr: ScenarioResult) -> None:
    """Print structured summary of a scenario result."""
    logger.info("\n" + "=" * 70)
    logger.info("📋 SCENARIO SUMMARY: %s", sr.scenario.upper())
    logger.info("=" * 70)
    logger.info("  Description: %s", sr.description)
    logger.info("  Timestamp: %s", sr.timestamp)
    logger.info("  Duration: %.1f seconds", sr.duration_seconds)
    logger.info("  Subsectors tested: %d", sr.subsectors_tested)
    logger.info("  Companies tested: %d", sr.companies_tested)

    if sr.quality_summary:
        logger.info("\n  📊 Quality Summary:")
        for k, v in sr.quality_summary.items():
            logger.info("    %s: %s", k, v)

    logger.info("\n  📝 Subsector Details:")
    for sub_r in sr.subsector_results:
        icon = "✅" if "GOOD" in sub_r.verdict else "⚠️" if "PARTIAL" in sub_r.verdict else "❌"
        logger.info("    %s %s (%d cos): %s", icon, sub_r.subsector, sub_r.n_companies, sub_r.verdict)
        for cr in sub_r.companies[:8]:
            bar = "█" * int(cr.data_completeness * 5) + "░" * (5 - int(cr.data_completeness * 5))
            logger.info("      %s [%s] %s — %s", cr.symbol, bar, f"{cr.data_completeness:.0%}", cr.verdict)

    logger.info("\n  🏆 Overall: %s", sr.overall_verdict)
    logger.info("=" * 70)


def _serialize_scenario(sr: ScenarioResult) -> dict[str, Any]:
    """Convert scenario result to JSON-serializable dict."""
    result: dict[str, Any] = {
        "scenario": sr.scenario,
        "description": sr.description,
        "timestamp": sr.timestamp,
        "duration_seconds": sr.duration_seconds,
        "subsectors_tested": sr.subsectors_tested,
        "companies_tested": sr.companies_tested,
        "overall_score": sr.overall_score,
        "overall_verdict": sr.overall_verdict,
        "quality_summary": sr.quality_summary,
        "subsector_results": [],
    }
    for sub_r in sr.subsector_results:
        sub_dict: dict[str, Any] = {
            "subsector": sub_r.subsector,
            "sector": sub_r.sector,
            "n_companies": sub_r.n_companies,
            "n_with_metrics": sub_r.n_with_metrics,
            "peer_normalization_working": sub_r.peer_normalization_working,
            "verdict": sub_r.verdict,
            "distribution_checks": sub_r.distribution_checks,
            "companies": [],
        }
        for cr in sub_r.companies:
            comp_dict = {
                "symbol": cr.symbol,
                "company_name": cr.company_name,
                "subsector": cr.subsector,
                "sector": cr.sector,
                "growth_method": cr.growth_method,
                "growth_period": cr.growth_period,
                "price_period": cr.price_period,
                "data_completeness": cr.data_completeness,
                "has_normalization_exclusions": cr.has_normalization_exclusions,
                "exclusion_reasons": cr.exclusion_reasons,
                "verdict": cr.verdict,
                "metric_checks": [
                    {"metric": mc.metric, "value": mc.value, "has_value": mc.has_value,
                     "is_reasonable": mc.is_reasonable, "reason": mc.reason}
                    for mc in cr.metric_checks
                ],
                "z_score_checks": [
                    {"metric": zc.metric, "value": zc.value, "has_value": zc.has_value,
                     "is_reasonable": zc.is_reasonable, "reason": zc.reason}
                    for zc in cr.z_score_checks
                ],
            }
            sub_dict["companies"].append(comp_dict)
        result["subsector_results"].append(sub_dict)
    return result


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Live API Integration Test for Market State Engine v2")
    parser.add_argument("--professional-only", action="store_true")
    parser.add_argument("--beginner-only", action="store_true")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════════════════════════════════╗")
    logger.info("║  Market State Engine v2 — Live API Integration Test             ║")
    logger.info("║  Methodology: 2026-09-13-validity-v2                            ║")
    logger.info("║  Date: %s                                     ║", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("╚══════════════════════════════════════════════════════════════════╝")

    client = SectorsClient()
    results: list[ScenarioResult] = []

    if not args.beginner_only:
        pro_result = run_professional_scenario(client)
        print_scenario_summary(pro_result)
        results.append(pro_result)

    if not args.professional_only:
        beg_result = run_beginner_scenario(client)
        print_scenario_summary(beg_result)
        results.append(beg_result)

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"live_test_{timestamp_str}.json"
    output_data = {
        "test_run": {
            "timestamp": datetime.now(UTC).isoformat(),
            "methodology_version": "2026-09-13-validity-v2",
            "engine_version": "market-intelligence-agent 0.1.0",
            "args": vars(args),
        },
        "scenarios": [_serialize_scenario(r) for r in results],
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    logger.info("\n📁 Results saved to: %s", output_file)

    # Final verdict
    logger.info("\n" + "=" * 70)
    logger.info("🏁 FINAL VERDICTS")
    logger.info("=" * 70)
    all_pass = True
    for r in results:
        icon = "✅" if "PASS" in r.overall_verdict else "⚠️" if "MARGINAL" in r.overall_verdict else "❌"
        logger.info("  %s %s: %s", icon, r.scenario.upper(), r.overall_verdict)
        if "FAIL" in r.overall_verdict:
            all_pass = False
    logger.info("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
