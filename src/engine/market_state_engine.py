"""Market State Engine — Pipeline Orchestrator (Task T2.4).

Integrates all Hari 2 components into a single pipeline:
1. BUILD UNIVERSE — taxonomy.py: fetch subsectors, exclude financials
2. FETCH DATA — SectorsClient: quarterly financials + daily prices (incremental cache)
3. CALCULATE METRICS — metrics.py: raw metrics per company
4. NORMALIZE — stats.py: peer_z per subsector
5. ASSEMBLE — CompanyState list with provenance

This is the main entry point for the quantitative engine.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.client.sectors_client import SectorsClient
from src.engine.metrics import calculate_metrics, extract_market_context
from src.engine.models import (
    CompanyInfo,
    CompanyState,
    MarketStateResult,
    MetricSet,
    PeerZScores,
    SubsectorProfile,
    UniverseStats,
)
from src.engine.stats import compute_subsector_zscores, is_finite_number
from src.engine.taxonomy import build_universe, is_financial_sector

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

DEFAULT_N_QUARTERS = 8
"""Number of quarters to request from the API. 8 enables YoY comparison
(latest quarter vs same quarter in prior year)."""

DEFAULT_PRICE_WINDOW_DAYS = 30
"""Inclusive calendar window used for every company's daily-price request."""


def _as_date(value: date | str | None, name: str) -> date | None:
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO date") from error
        if parsed.isoformat() == value:
            return parsed
    raise ValueError(f"{name} must be an ISO date")


def _price_window(
    price_start: date | str | None, price_end: date | str | None
) -> tuple[date, date]:
    """Return an explicit inclusive 30-day window unless both bounds are supplied."""
    end = _as_date(price_end, "price_end") or datetime.now(UTC).date()
    start = _as_date(price_start, "price_start") or (end - timedelta(days=DEFAULT_PRICE_WINDOW_DAYS - 1))
    if start > end:
        raise ValueError("price_start must be on or before price_end")
    return start, end


def _sanitize_universe(
    universe: dict[str, list[CompanyInfo]],
) -> tuple[dict[str, list[CompanyInfo]], int, int]:
    """Reject financials and globally deduplicate symbols before data fetching.

    A symbol assigned to more than one subsector is kept only at its first
    occurrence. This prevents metadata keyed by symbol from silently being
    overwritten by a later subsector assignment.
    """
    sanitized: dict[str, list[CompanyInfo]] = {}
    seen_symbols: set[str] = set()
    excluded_financial = 0
    duplicates = 0
    for subsector, companies in universe.items():
        accepted: list[CompanyInfo] = []
        for company in companies:
            if is_financial_sector(company.sector):
                excluded_financial += 1
                continue
            if company.symbol in seen_symbols:
                duplicates += 1
                logger.warning(
                    "Universe: duplicate symbol %s in subsector %s ignored", company.symbol, subsector
                )
                continue
            seen_symbols.add(company.symbol)
            accepted.append(company)
        if accepted:
            sanitized[subsector] = accepted
    return sanitized, excluded_financial, duplicates


def _comparable_metrics(
    metrics_map: dict[str, MetricSet], metadata: dict[str, dict[str, Any]]
) -> tuple[dict[str, MetricSet], dict[str, str], dict[str, dict[str, str]]]:
    """Normalize one observed period per metric family, preserving raw values.

    ponytail: largest exact-period cohort, latest on ties; add separate cohort
    profiles if coverage warrants it. This does not establish data freshness.
    """
    comparable = {sym: replace(ms) for sym, ms in metrics_map.items()}
    periods: dict[str, str] = {}
    exclusions: dict[str, dict[str, str]] = {sym: {} for sym in metrics_map}
    families = (
        (("revenue_growth", "earnings_growth", "margin_change"), "growth_period"),
        (("roe_ttm",), "financial_period"),
        (("price_return",), "price_period"),
    )
    for fields, period_key in families:
        counts: Counter[str] = Counter()
        for sym, ms in metrics_map.items():
            meta = metadata[sym]
            if period_key == "growth_period" and meta["growth_method"] != "YoY":
                continue
            if meta[period_key] and any(is_finite_number(getattr(ms, f)) for f in fields):
                counts[meta[period_key]] += 1
        chosen = max(counts, key=lambda p: (counts[p], p)) if counts else None
        for name in fields:
            if chosen:
                periods[name] = chosen
            for sym in metrics_map:
                meta = metadata[sym]
                reason = None
                if period_key == "growth_period" and meta["growth_method"] != "YoY":
                    reason = "yoy_required"
                elif chosen is None or meta[period_key] != chosen:
                    reason = "period_mismatch_or_missing"
                if reason:
                    setattr(comparable[sym], name, None)
                    exclusions[sym][name] = reason
    return comparable, periods, exclusions


# ──────────────────────────────────────────────────────────────────────
# Pipeline Orchestrator
# ──────────────────────────────────────────────────────────────────────


class MarketStateEngine:
    """Orchestrates the full Hari 2 quantitative pipeline.

    Usage:
        client = SectorsClient()
        engine = MarketStateEngine(client)
        result = engine.compute_market_state()
    """

    def __init__(self, client: SectorsClient):
        self.client = client

    def build_universe_map(self) -> dict[str, list[CompanyInfo]]:
        """T2.1: Build universe of non-financial IDX companies.

        Returns:
            Dict mapping subsector slug → list of CompanyInfo.
        """
        return build_universe(self.client)

    def fetch_company_data(
        self,
        symbol: str,
        n_quarters: int = DEFAULT_N_QUARTERS,
        price_start: date | None = None,
        price_end: date | None = None,
    ) -> dict[str, Any]:
        """Fetch quarterly financials + daily prices for one company.

        Uses SectorsClient with automatic caching — previously fetched
        data is served from local snapshot cache.

        Returns:
            Dict with keys 'quarterly' and 'daily', each containing
            the raw API response data (list of dicts).
        """
        quarterly: list[dict[str, Any]] = []
        daily: list[dict[str, Any]] = []

        try:
            quarterly = self.client.get_financials_quarterly(symbol, n_quarters=n_quarters)
        except Exception as e:
            logger.warning("Failed to fetch quarterly data for %s: %s", symbol, e)

        try:
            daily = self.client.get_daily_transactions(
                symbol,
                start=price_start.isoformat() if price_start else None,
                end=price_end.isoformat() if price_end else None,
            )
        except Exception as e:
            logger.warning("Failed to fetch daily data for %s: %s", symbol, e)

        return {"quarterly": quarterly, "daily": daily}

    def compute_market_state(
        self,
        universe: dict[str, list[CompanyInfo]] | None = None,
        n_quarters: int = DEFAULT_N_QUARTERS,
        price_start: date | str | None = None,
        price_end: date | str | None = None,
    ) -> MarketStateResult:
        """Execute the full Hari 2 pipeline.

        Pipeline steps:
        1. Build universe (if not provided)
        2. Fetch financial + daily data per company (cache-aware)
        3. Calculate raw metrics per company
        4. Group by subsector → compute peer_z
        5. Assemble CompanyState list with provenance

        Args:
            universe: Pre-built universe map. If None, builds from API.
            n_quarters: Number of quarters to request (default 8 for YoY).
            price_start: Inclusive ISO date for daily data. Defaults to 30
                calendar days before ``price_end``.
            price_end: Inclusive ISO date for daily data. Defaults to today
                in UTC.

        Returns:
            MarketStateResult with all CompanyState objects and profiles.
        """
        timestamp = datetime.now(UTC).isoformat()
        methodology_notes: list[str] = []
        resolved_price_start, resolved_price_end = _price_window(price_start, price_end)

        # ── Step 1: Universe ────────────────────────────────────
        if universe is None:
            logger.info("Step 1/4: Building universe from Sectors API...")
            universe = self.build_universe_map()
        else:
            logger.info("Step 1/4: Using pre-built universe (%d subsectors)", len(universe))

        universe, excluded_financial, duplicate_symbols = _sanitize_universe(universe)
        if excluded_financial:
            logger.info("Universe: excluded %d financial company entries", excluded_financial)
        if duplicate_symbols:
            methodology_notes.append(
                f"universe_deduplication: ignored {duplicate_symbols} duplicate symbol assignment(s)"
            )

        total_companies = sum(len(v) for v in universe.values())
        logger.info(
            "Universe: %d subsectors, %d total companies",
            len(universe),
            total_companies,
        )

        # ── Step 2 & 3: Fetch data + Calculate metrics ──────────
        logger.info("Step 2-3/4: Fetching data and computing metrics...")

        # Collect metrics grouped by subsector
        subsector_metrics: dict[str, dict[str, MetricSet]] = {}
        company_metadata: dict[str, dict[str, Any]] = {}
        fetch_count = 0

        for subsector, companies in universe.items():
            subsector_metrics[subsector] = {}

            for ci in companies:
                fetch_count += 1
                if fetch_count % 50 == 0 or fetch_count == total_companies:
                    logger.info(
                        "  Progress: %d/%d companies fetched...",
                        fetch_count,
                        total_companies,
                    )

                raw_data = self.fetch_company_data(
                    ci.symbol,
                    n_quarters,
                    price_start=resolved_price_start,
                    price_end=resolved_price_end,
                )
                quarterly = raw_data.get("quarterly", [])
                daily = raw_data.get("daily", [])

                # The calculator validates/sorts observations at its boundary.
                metrics, growth_method, growth_period, price_period = calculate_metrics(
                    quarterly, daily
                )
                context = extract_market_context(quarterly, daily)

                subsector_metrics[subsector][ci.symbol] = metrics
                company_metadata[ci.symbol] = {
                    "info": ci,
                    "growth_method": growth_method,
                    "growth_period": growth_period,
                    "price_period": price_period,
                    "financial_period": context["financial_period"],
                    "context": context,
                }

        # ── Step 4: Normalize per subsector ─────────────────────
        logger.info("Step 4/4: Computing peer_z per subsector...")

        all_companies: list[CompanyState] = []
        all_profiles: dict[str, SubsectorProfile] = {}
        total_with_data = 0

        for subsector, metrics_map in subsector_metrics.items():
            if not metrics_map:
                continue

            # Get sector from first company
            first_sym = next(iter(metrics_map))
            sector = company_metadata[first_sym]["info"].sector

            comparable, periods, exclusions = _comparable_metrics(metrics_map, company_metadata)
            z_scores, profile = compute_subsector_zscores(
                comparable, subsector=subsector, sector=sector
            )
            profile.normalization_periods = periods
            all_profiles[subsector] = profile

            # Assemble CompanyState for each company
            for sym, ms in metrics_map.items():
                meta = company_metadata[sym]
                ci = meta["info"]
                zs = z_scores.get(sym, PeerZScores())

                has_any_metric = any(
                    getattr(ms, f) is not None
                    for f in (
                        "revenue_growth",
                        "earnings_growth",
                        "margin_change",
                        "roe_ttm",
                        "price_return",
                    )
                )
                if has_any_metric:
                    total_with_data += 1

                cs = CompanyState(
                    symbol=ci.symbol,
                    company_name=ci.company_name,
                    sector=ci.sector,
                    subsector=ci.subsector,
                    raw_metrics=ms,
                    peer_z=zs,
                    growth_period=meta["growth_period"],
                    growth_method=meta["growth_method"],
                    price_period=meta["price_period"],
                    data_timestamp=timestamp,
                    normalization_exclusions=exclusions[sym],
                    market_cap=meta["context"]["market_cap"],
                    market_cap_date=meta["context"]["market_cap_date"],
                    latest_equity=meta["context"]["latest_equity"],
                    financial_period=meta["context"]["financial_period"],
                    price_end_date=meta["context"]["price_end_date"],
                    traded_value_proxy=meta["context"]["traded_value_proxy"],
                    traded_value_observation_count=meta["context"]["traded_value_observation_count"],
                    volume_unit_verified=meta["context"]["volume_unit_verified"],
                    earnings_growth_from_loss_base=meta["context"][
                        "earnings_growth_from_loss_base"
                    ],
                )
                all_companies.append(cs)

        # Sort by subsector then symbol for deterministic output
        all_companies.sort(key=lambda c: (c.subsector, c.symbol))

        # Methodology notes
        methodology_notes.append(
            "peer_z formula: z = (x - median) / (1.4826 × MAD), "
            "consistency factor k=1.4826 (Iglewicz & Hoaglin, 1993)"
        )
        methodology_notes.append("Winsorizing at 1%/99% for subsectors with n ≥ 5")
        methodology_notes.append(
            f"n_quarters={n_quarters}; QoQ is display-only and excluded from growth peer_z. "
            "Each metric family uses its largest exact-period cohort (latest on ties)."
        )
        methodology_notes.append(
            "daily_price_window="
            f"{resolved_price_start.isoformat()} to {resolved_price_end.isoformat()} (inclusive, requested); "
            "traded-value proxy uses up to 20 dated observations and is not filterable until "
            "the source volume unit is verified."
        )
        methodology_notes.append(
            "methodology_version=2026-09-13-validity-v2; n<3 or MAD=0 gives None; "
            "n=3..7 is flagged low_sample. Raw numerators remain unbounded. "
            "Scores are descriptive, not calibrated probabilities or validated alpha."
        )
        methodology_notes.append(
            "data_timestamp is computation time, not source publication/retrieval time; "
            "equal price endpoints do not verify liquidity or corporate-action adjustment."
        )

        universe_stats = UniverseStats(
            total_subsectors_scanned=len(universe),
            total_companies_universe=total_companies,
            total_with_data=total_with_data,
            total_excluded_financial=excluded_financial,
        )

        result = MarketStateResult(
            companies=all_companies,
            subsector_profiles=all_profiles,
            universe_stats=universe_stats,
            methodology_notes=methodology_notes,
        )

        logger.info(
            "Pipeline complete: %d companies processed, %d with valid metrics, "
            "%d subsector profiles",
            len(all_companies),
            total_with_data,
            len(all_profiles),
        )

        return result
