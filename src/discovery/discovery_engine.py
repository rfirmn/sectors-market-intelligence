"""Deterministic, network-free opportunity discovery over ``CompanyState``.

Lens scores are frozen from the complete snapshot before any mandate filter is
applied. Narrowing a watchlist therefore cannot change a remaining company's
reference cohort or score.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from datetime import date, datetime
from typing import Any

from src.discovery.models import (
    DiscoveryResult,
    EvidenceStandard,
    FilterFunnel,
    LensCoverage,
    LensEvaluation,
    LensName,
    NumericRange,
    OpportunityCandidate,
    ResearchMandate,
)
from src.engine.models import CompanyState

_UNKNOWN_PERIOD = "unknown"
_MIN_EXPLORATORY_COHORT = 3
_MIN_STANDARD_COHORT = 8


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
    return None


def _read(company: CompanyState, *names: str) -> Any:
    """Read current and planned context fields without coupling to a wrapper."""
    containers: list[object] = [company]
    for context_name in ("discovery_context", "market_context", "context", "provenance"):
        context = getattr(company, context_name, None)
        if context is not None:
            containers.append(context)
    for container in containers:
        for name in names:
            if isinstance(container, dict) and name in container:
                return container[name]
            value = getattr(container, name, None)
            if value is not None:
                return value
    return None


def _metric(company: CompanyState, name: str) -> float | None:
    return _finite(getattr(company.raw_metrics, name, None))


def _z(company: CompanyState, name: str) -> float | None:
    return _finite(getattr(company.peer_z, name, None))


def empirical_midrank(value: float, values: Iterable[float]) -> float:
    """Empirical P(x): equal values receive identical midranks."""
    cohort = tuple(values)
    if not cohort:
        raise ValueError("cannot rank an empty cohort")
    return (sum(item < value for item in cohort) + 0.5 * sum(item == value for item in cohort)) / len(cohort)


def _period(*values: object) -> str:
    return " | ".join(str(value) if value else _UNKNOWN_PERIOD for value in values)


def _has_unknown_period(period: str) -> bool:
    return _UNKNOWN_PERIOD in period.split(" | ")


class DiscoveryEngine:
    """Calculate reference scores then apply an investor's research mandate."""

    def discover(
        self,
        companies: Iterable[CompanyState],
        mandate: ResearchMandate | None = None,
        *,
        snapshot_date: date | datetime | str | None = None,
    ) -> DiscoveryResult:
        mandate = mandate or ResearchMandate()
        materialized = sorted(companies, key=lambda item: (item.subsector, item.symbol))
        evaluations = self._evaluate_all(materialized, mandate.evidence_standard)
        return self._apply_mandate(materialized, evaluations, mandate, _date(snapshot_date))

    def _evaluate_all(
        self, companies: list[CompanyState], standard: EvidenceStandard
    ) -> dict[str, dict[LensName, LensEvaluation]]:
        results = {company.symbol: {} for company in companies}
        for lens in LensName:
            self._evaluate_lens(companies, results, lens, standard)
        return results

    def _lens_inputs(
        self, company: CompanyState, lens: LensName
    ) -> tuple[dict[str, float], str, tuple[str, ...], int]:
        if lens == LensName.DISLOCATION:
            values = {
                "z_revenue_growth": _z(company, "z_revenue_growth"),
                "z_earnings_growth": _z(company, "z_earnings_growth"),
                "z_margin_change": _z(company, "z_margin_change"),
                "z_price_return": _z(company, "z_price_return"),
            }
            period = _period(_read(company, "growth_period"), _read(company, "price_period", "price_end_date"))
        elif lens == LensName.GROWTH:
            values = {
                "z_revenue_growth": _z(company, "z_revenue_growth"),
                "z_earnings_growth": _z(company, "z_earnings_growth"),
                "revenue_growth": _metric(company, "revenue_growth"),
                "earnings_growth": _metric(company, "earnings_growth"),
            }
            period = _period(_read(company, "growth_period"))
        elif lens == LensName.PROFITABILITY:
            values = {
                "operating_margin": _metric(company, "operating_margin"),
                "margin_change": _metric(company, "margin_change"),
            }
            period = _period(_read(company, "growth_period", "financial_period"))
        else:
            values = {
                "pb": _metric(company, "pb"),
                "market_cap": _finite(_read(company, "market_cap", "market_cap_idr")),
                "equity": _finite(_read(company, "equity", "latest_equity", "total_equity")),
            }
            period = _period(
                _read(company, "financial_period", "financial_date", "equity_date"),
                _read(company, "market_cap_date"),
            )
        missing = [name for name, value in values.items() if value is None]
        if lens == LensName.VALUE:
            if values["pb"] is not None and values["pb"] <= 0:
                missing.append("pb_must_be_positive")
            if values["market_cap"] is not None and values["market_cap"] < 0:
                missing.append("market_cap_must_be_nonnegative")
            if values["equity"] is not None and values["equity"] <= 0:
                missing.append("equity_must_be_positive")
        return ({key: value for key, value in values.items() if value is not None}, period, tuple(sorted(set(missing))), len(values))

    def _evaluate_lens(
        self,
        companies: list[CompanyState],
        destination: dict[str, dict[LensName, LensEvaluation]],
        lens: LensName,
        standard: EvidenceStandard,
    ) -> None:
        complete: dict[tuple[str, str], list[tuple[CompanyState, dict[str, float]]]] = defaultdict(list)
        source: dict[str, tuple[dict[str, float], str, tuple[str, ...], int]] = {}
        for company in companies:
            inputs, period, invalid, expected = self._lens_inputs(company, lens)
            source[company.symbol] = (inputs, period, invalid, expected)
            if not invalid and len(inputs) == expected:
                complete[(company.subsector, period)].append((company, inputs))

        selected: dict[str, tuple[str, list[tuple[CompanyState, dict[str, float]]]]] = {}
        for subsector in {company.subsector for company in companies}:
            options = [(period, group) for (subsector_key, period), group in complete.items() if subsector_key == subsector]
            if options:
                selected[subsector] = max(options, key=lambda item: (len(item[1]), item[0]))

        for company in companies:
            inputs, period, invalid, expected = source[company.symbol]
            if invalid or len(inputs) != expected:
                destination[company.symbol][lens] = LensEvaluation(
                    lens=lens, status="not_evaluable", period=period,
                    reasons=tuple(f"missing_or_invalid:{item}" for item in invalid),
                )
                continue
            chosen = selected.get(company.subsector)
            if chosen is None:
                destination[company.symbol][lens] = LensEvaluation(
                    lens=lens, status="not_evaluable", period=period, reasons=("no_complete_case_cohort",)
                )
                continue
            chosen_period, group = chosen
            if period != chosen_period:
                destination[company.symbol][lens] = LensEvaluation(
                    lens=lens, status="period_mismatch", period=period, reasons=("period_mismatch",)
                )
                continue
            n = len(group)
            warning = ("period_unknown",) if _has_unknown_period(chosen_period) else ()
            if n < _MIN_EXPLORATORY_COHORT:
                destination[company.symbol][lens] = LensEvaluation(
                    lens=lens, status="insufficient_cohort", cohort_size=n, period=chosen_period,
                    inputs=inputs, reasons=("cohort_below_exploratory_minimum",) + warning,
                )
                continue
            evaluation = self._score_lens(lens, inputs, group, chosen_period)
            if n < _MIN_STANDARD_COHORT:
                evaluation = evaluation.model_copy(update={
                    "status": "low_sample", "usable": standard == EvidenceStandard.EXPLORATORY,
                    "reasons": evaluation.reasons + ("low_sample",) + warning,
                })
            else:
                evaluation = evaluation.model_copy(update={
                    "status": "ok", "usable": True, "reasons": evaluation.reasons + warning,
                })
            destination[company.symbol][lens] = evaluation

    def _score_lens(
        self,
        lens: LensName,
        inputs: dict[str, float],
        group: list[tuple[CompanyState, dict[str, float]]],
        period: str,
    ) -> LensEvaluation:
        n = len(group)
        if lens == LensName.DISLOCATION:
            def discrepancy_of(data: dict[str, float]) -> float:
                return (
                    (data["z_revenue_growth"] + data["z_earnings_growth"] + data["z_margin_change"])
                    / 3
                    - data["z_price_return"]
                )

            discrepancy = discrepancy_of(inputs)
            return LensEvaluation(lens=lens, score=empirical_midrank(discrepancy, [discrepancy_of(item) for _, item in group]), matched=discrepancy > 1.0, usable=True, status="ok", cohort_size=n, period=period, inputs={**inputs, "discrepancy": discrepancy})
        if lens == LensName.GROWTH:
            def growth_of(data: dict[str, float]) -> float:
                return (data["z_revenue_growth"] + data["z_earnings_growth"]) / 2

            growth = growth_of(inputs)
            return LensEvaluation(lens=lens, score=empirical_midrank(growth, [growth_of(item) for _, item in group]), matched=inputs["revenue_growth"] > 0 and inputs["earnings_growth"] > 0 and growth > 0, usable=True, status="ok", cohort_size=n, period=period, inputs={**inputs, "growth_composite": growth})
        if lens == LensName.PROFITABILITY:
            margins = [item["operating_margin"] for _, item in group]
            changes = [item["margin_change"] for _, item in group]
            margin_score = empirical_midrank(inputs["operating_margin"], margins)
            change_score = empirical_midrank(inputs["margin_change"], changes)
            score = (margin_score + change_score) / 2
            return LensEvaluation(lens=lens, score=score, matched=inputs["operating_margin"] > 0 and inputs["margin_change"] > 0 and score > 0.5, usable=True, status="ok", cohort_size=n, period=period, inputs={**inputs, "operating_margin_percentile": margin_score, "margin_change_percentile": change_score})
        pbs = [item["pb"] for _, item in group]
        percentile = empirical_midrank(inputs["pb"], pbs)
        return LensEvaluation(lens=lens, score=1 - percentile, matched=inputs["pb"] < statistics.median(pbs), usable=True, status="ok", cohort_size=n, period=period, inputs={**inputs, "pb_percentile": percentile, "peer_pb_median": float(statistics.median(pbs))})

    def _apply_mandate(
        self,
        companies: list[CompanyState],
        evaluations: dict[str, dict[LensName, LensEvaluation]],
        mandate: ResearchMandate,
        as_of: date | None,
    ) -> DiscoveryResult:
        active = {lens for lens, weight in mandate.normalized_weights.items() if weight > 0}
        excluded: Counter[str] = Counter()
        filtered: list[CompanyState] = []
        for company in companies:
            reasons = self._filter_reasons(company, mandate, as_of)
            if reasons:
                excluded.update(reasons)
            else:
                filtered.append(company)
        valid: list[CompanyState] = []
        matching: list[CompanyState] = []
        for company in filtered:
            company_evaluations = evaluations[company.symbol]
            unavailable = [lens for lens in active if not company_evaluations[lens].usable or company_evaluations[lens].score is None]
            if unavailable:
                excluded.update(f"active_lens_unavailable:{lens.value}" for lens in unavailable)
                continue
            valid.append(company)
            if any(company_evaluations[lens].matched for lens in active):
                matching.append(company)
            else:
                excluded["no_active_lens_match"] += 1
        ranked: list[tuple[CompanyState, float, dict[LensName, float]]] = []
        for company in matching:
            contributions = {lens: 100 * mandate.normalized_weights[lens] * float(evaluations[company.symbol][lens].score) for lens in active}
            ranked.append((company, sum(contributions.values()), contributions))
        ranked.sort(key=lambda item: (-item[1], item[0].symbol))
        limited: list[tuple[CompanyState, float, dict[LensName, float], int]] = []
        per_subsector: Counter[str] = Counter()
        for original_rank, (company, fit, contributions) in enumerate(ranked, start=1):
            if mandate.max_per_subsector is not None and per_subsector[company.subsector] >= mandate.max_per_subsector:
                excluded["subsector_limit"] += 1
                continue
            per_subsector[company.subsector] += 1
            limited.append((company, fit, contributions, original_rank))
        candidates = tuple(self._candidate(company, fit, contributions, original_rank, rank, evaluations[company.symbol], active) for rank, (company, fit, contributions, original_rank) in enumerate(limited[:mandate.top_k], start=1))
        warnings = []
        if not candidates:
            warnings.append("No candidates met the mandate; filters and lens evidence were not relaxed.")
        if mandate.filters.transaction_activity is not None:
            warnings.append("Transaction activity is a source-dependent proxy, not a liquidity guarantee.")
        return DiscoveryResult(
            mandate=mandate, effective_weights=mandate.normalized_weights,
            snapshot_date=as_of.isoformat() if as_of is not None else None, candidates=candidates,
            coverage=self._coverage(companies, evaluations),
            funnel=FilterFunnel(total=len(companies), passed_filters=len(filtered), passed_active_lenses=len(valid), matched_an_active_lens=len(matching), after_subsector_limit=len(limited), returned=len(candidates), excluded=dict(sorted(excluded.items()))),
            exclusions=dict(sorted(excluded.items())), warnings=tuple(warnings),
        )

    def _filter_reasons(self, company: CompanyState, mandate: ResearchMandate, as_of: date | None) -> list[str]:
        filters, reasons = mandate.filters, []
        def membership(value: str, include: tuple[str, ...], exclude: tuple[str, ...], name: str) -> None:
            if value in exclude:
                reasons.append(f"excluded_{name}")
            elif include and value not in include:
                reasons.append(f"not_included_{name}")
        membership(company.sector, filters.include_sectors, filters.exclude_sectors, "sector")
        membership(company.subsector, filters.include_subsectors, filters.exclude_subsectors, "subsector")
        membership(company.symbol, filters.include_symbols, filters.exclude_symbols, "symbol")
        ranges: tuple[tuple[str, NumericRange | None, Callable[[], float | None]], ...] = (
            ("revenue_growth", filters.revenue_growth, lambda: _metric(company, "revenue_growth")),
            ("earnings_growth", filters.earnings_growth, lambda: _metric(company, "earnings_growth")),
            ("operating_margin", filters.operating_margin, lambda: _metric(company, "operating_margin")),
            ("margin_change", filters.margin_change, lambda: _metric(company, "margin_change")),
            ("pb", filters.pb, lambda: _metric(company, "pb")),
            ("price_return", filters.price_return, lambda: _metric(company, "price_return")),
            ("market_cap", filters.market_cap, lambda: _finite(_read(company, "market_cap", "market_cap_idr"))),
            ("transaction_activity", filters.transaction_activity, lambda: _finite(_read(company, "traded_value_proxy", "transaction_activity_proxy"))),
        )
        for name, numeric_range, getter in ranges:
            if numeric_range is None:
                continue
            if name == "transaction_activity" and not bool(_read(company, "volume_unit_verified", "transaction_activity_unit_verified")):
                reasons.append("transaction_activity_unavailable_or_unit_unverified")
            else:
                value = getter()
                if value is None:
                    reasons.append(f"missing_filter_metric:{name}")
                elif not numeric_range.contains(value):
                    reasons.append(f"filter_outside_range:{name}")
        self._age_reason(reasons, "price", filters.price_age_days, _read(company, "price_end_date"), as_of)
        self._age_reason(reasons, "financial", filters.financial_age_days, _read(company, "financial_period", "financial_date", "equity_date"), as_of)
        return reasons

    @staticmethod
    def _age_reason(reasons: list[str], name: str, bound: NumericRange | None, observed: object, as_of: date | None) -> None:
        if bound is None:
            return
        observed_date = _date(observed)
        if as_of is None or observed_date is None or observed_date > as_of:
            reasons.append(f"missing_filter_metric:{name}_age_days")
        elif not bound.contains(float((as_of - observed_date).days)):
            reasons.append(f"filter_outside_range:{name}_age_days")

    @staticmethod
    def _coverage(companies: list[CompanyState], evaluations: dict[str, dict[LensName, LensEvaluation]]) -> dict[LensName, LensCoverage]:
        result = {}
        for lens in LensName:
            items = [evaluations[company.symbol][lens] for company in companies]
            cohorts = Counter(f"{company.subsector}:{item.period or 'unknown'}" for company, item in zip(companies, items, strict=True) if item.cohort_size)
            result[lens] = LensCoverage(lens=lens, evaluated=sum(item.score is not None for item in items), usable_standard=sum(item.status == "ok" and item.usable for item in items), usable_exploratory=sum(item.status in {"ok", "low_sample"} and item.score is not None for item in items), matched=sum(item.matched for item in items), cohorts=dict(sorted(cohorts.items())))
        return result

    @staticmethod
    def _candidate(company: CompanyState, fit: float, contributions: dict[LensName, float], original_rank: int, rank: int, evaluations: dict[LensName, LensEvaluation], active: set[LensName]) -> OpportunityCandidate:
        discrepancy = evaluations[LensName.DISLOCATION].inputs.get("discrepancy")
        label = "NOT_EVALUABLE" if discrepancy is None else "HIGH" if discrepancy > 1.5 else "MEDIUM" if discrepancy > 1.0 else "NONE"
        matched = tuple(lens for lens in LensName if lens in active and evaluations[lens].matched)
        evidence = tuple(f"{lens.value}: score={evaluations[lens].score:.6f}; contribution={contributions[lens]:.6f}" for lens in LensName if lens in contributions and evaluations[lens].matched)
        limitations = tuple(f"{lens.value}: {reason}" for lens in LensName for reason in evaluations[lens].reasons)
        return OpportunityCandidate(symbol=company.symbol, company_name=company.company_name, sector=company.sector, subsector=company.subsector, research_fit=fit, rank_before_subsector_limit=original_rank, rank=rank, weighted_contributions=contributions, matched_lenses=matched, lens_evaluations=evaluations, discrepancy=discrepancy, discrepancy_label=label, evidence=evidence, limitations=limitations)


def discover_opportunities(companies: Iterable[CompanyState], mandate: ResearchMandate | None = None, *, snapshot_date: date | datetime | str | None = None) -> DiscoveryResult:
    """Functional API for one deterministic discovery search."""
    return DiscoveryEngine().discover(companies, mandate, snapshot_date=snapshot_date)
