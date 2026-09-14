"""Independent behavioural tests for the Day 3 discovery domain.

The expected numbers in this module are deliberately calculated from the
published equations.  They must not call the discovery engine's helpers: that
would make a shared formula bug look like a passing test.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from src.discovery.discovery_engine import DiscoveryEngine, discover_opportunities
from src.discovery.models import (
    DisplayMode,
    EvidenceStandard,
    LensName,
    LensWeights,
    MandateFilters,
    NumericRange,
    PresetName,
    ResearchMandate,
)
from src.engine.models import CompanyState, MetricSet, PeerZScores


def _midrank(value: float, values: list[float]) -> float:
    """The documented empirical percentile, independently implemented."""
    return (sum(item < value for item in values) + 0.5 * sum(item == value for item in values)) / len(values)


def _company(
    symbol: str,
    *,
    subsector: str = "industrials",
    sector: str = "industry",
    z_revenue: float | None = 0.0,
    z_earnings: float | None = 0.0,
    z_margin: float | None = 0.0,
    z_price: float | None = 0.0,
    revenue_growth: float | None = 0.10,
    earnings_growth: float | None = 0.10,
    operating_margin: float | None = 0.10,
    margin_change: float | None = 0.01,
    price_return: float | None = 0.05,
    pb: float | None = 2.0,
    market_cap: float | None = 1_000_000_000.0,
    equity: float | None = 500_000_000.0,
) -> CompanyState:
    """Build a complete state using a single comparable reporting period."""
    state = CompanyState(
        symbol=symbol,
        company_name=f"{symbol} Corp",
        sector=sector,
        subsector=subsector,
        raw_metrics=MetricSet(
            revenue_growth=revenue_growth,
            earnings_growth=earnings_growth,
            operating_margin=operating_margin,
            margin_change=margin_change,
            price_return=price_return,
            pb=pb,
        ),
        peer_z=PeerZScores(
            z_revenue_growth=z_revenue,
            z_earnings_growth=z_earnings,
            z_margin_change=z_margin,
            z_price_return=z_price,
        ),
        growth_period="2026-Q2",
        price_period="2026-08-01 to 2026-08-30",
        financial_period="2026-06-30",
        price_end_date="2026-08-30",
        market_cap=market_cap,
    )
    # The Day 2 dataclass intentionally has no equity field.  Discovery's
    # bounded context reader supports an attached context object/dict.
    setattr(state, "discovery_context", {"equity": equity})
    return state


def _eight_complete(subsector: str = "industrials") -> list[CompanyState]:
    """Eight states with a clear best company for every Day 3 lens."""
    states: list[CompanyState] = []
    for index in range(8):
        # Increasing fundamentals and profitability, decreasing PB, and an
        # increasingly weak price response make the final item clearly match.
        states.append(
            _company(
                f"C{index}",
                subsector=subsector,
                z_revenue=[-2, -1, 0, 0.5, 1, 1.5, 2, 3][index],
                z_earnings=[-1, -0.5, 0, 0.25, 0.5, 1, 1.5, 2][index],
                z_margin=[-0.4, -0.2, 0, 0.1, 0.2, 0.3, 0.4, 0.5][index],
                z_price=[2, 1.5, 1, 0.8, 0.4, 0, -0.2, -0.5][index],
                revenue_growth=0.02 + index * 0.02,
                earnings_growth=0.01 + index * 0.02,
                operating_margin=0.04 + index * 0.03,
                margin_change=0.002 + index * 0.004,
                pb=4.0 - index * 0.4,
            )
        )
    return states


def _custom(**weights: float) -> ResearchMandate:
    return ResearchMandate(
        preset=PresetName.CUSTOM,
        weights=LensWeights(**weights),
        top_k=100,
    )


def _candidate(result, symbol: str):
    return next(item for item in result.candidates if item.symbol == symbol)


def test_all_four_lens_scores_follow_published_equations() -> None:
    states = _eight_complete()
    mandate = _custom(dislocation=25, growth=25, profitability=25, value=25)
    candidate = _candidate(discover_opportunities(states, mandate), "C7")

    target = states[-1]
    discrepancies = [
        (item.peer_z.z_revenue_growth + item.peer_z.z_earnings_growth + item.peer_z.z_margin_change) / 3
        - item.peer_z.z_price_return
        for item in states
    ]
    growths = [
        (item.peer_z.z_revenue_growth + item.peer_z.z_earnings_growth) / 2
        for item in states
    ]
    margins = [item.raw_metrics.operating_margin for item in states]
    changes = [item.raw_metrics.margin_change for item in states]
    pbs = [item.raw_metrics.pb for item in states]
    target_discrepancy = (
        (target.peer_z.z_revenue_growth + target.peer_z.z_earnings_growth + target.peer_z.z_margin_change) / 3
        - target.peer_z.z_price_return
    )
    target_growth = (target.peer_z.z_revenue_growth + target.peer_z.z_earnings_growth) / 2
    expected = {
        LensName.DISLOCATION: _midrank(target_discrepancy, discrepancies),
        LensName.GROWTH: _midrank(target_growth, growths),
        LensName.PROFITABILITY: (
            _midrank(target.raw_metrics.operating_margin, margins)
            + _midrank(target.raw_metrics.margin_change, changes)
        ) / 2,
        LensName.VALUE: 1 - _midrank(target.raw_metrics.pb, pbs),
    }

    assert candidate.discrepancy == pytest.approx(target_discrepancy)
    assert candidate.discrepancy_label == "HIGH"
    for lens, score in expected.items():
        evaluation = candidate.lens_evaluations[lens]
        assert evaluation.score == pytest.approx(score)
        assert evaluation.cohort_size == 8
        assert evaluation.usable is True
        assert evaluation.matched is True
    assert candidate.research_fit == pytest.approx(25 * sum(expected.values()))


def test_percentile_ties_are_equal_and_low_pb_scores_higher() -> None:
    states = _eight_complete()
    states[0].raw_metrics.pb = 1.0
    states[1].raw_metrics.pb = 1.0
    for index, state in enumerate(states[2:], start=2):
        state.raw_metrics.pb = float(index)

    result = discover_opportunities(states, ResearchMandate(preset=PresetName.VALUE, top_k=100))
    first, second = _candidate(result, "C0"), _candidate(result, "C1")
    tied_score = 1 - _midrank(1.0, [item.raw_metrics.pb for item in states])

    assert first.lens_evaluations[LensName.VALUE].score == pytest.approx(tied_score)
    assert second.lens_evaluations[LensName.VALUE].score == pytest.approx(tied_score)
    assert first.lens_evaluations[LensName.VALUE].score > _candidate(result, "C3").lens_evaluations[LensName.VALUE].score
    assert first.lens_evaluations[LensName.VALUE].matched is True


@pytest.mark.parametrize(
    ("z_revenue", "expected_label"),
    [(3.0, "NONE"), (4.5, "MEDIUM"), (4.5000001, "HIGH")],
)
def test_discrepancy_bounds_are_strict(z_revenue: float, expected_label: str) -> None:
    states = _eight_complete()
    # Other terms are zero, so this is exactly D=1.0, 1.5, or just above 1.5.
    states[0].peer_z = PeerZScores(z_revenue_growth=z_revenue, z_earnings_growth=0, z_margin_change=0, z_price_return=0)
    states[0].raw_metrics.pb = 0.1  # Value lens admits it to expose the label.

    candidate = _candidate(discover_opportunities(states, ResearchMandate(preset=PresetName.VALUE, top_k=100)), "C0")
    assert candidate.discrepancy == pytest.approx(z_revenue / 3)
    assert candidate.discrepancy_label == expected_label
    assert candidate.lens_evaluations[LensName.DISLOCATION].matched is (z_revenue / 3 > 1.0)


def test_dislocation_never_uses_partial_fundamentals() -> None:
    states = _eight_complete()
    states[0].peer_z = PeerZScores(z_revenue_growth=10, z_earnings_growth=None, z_margin_change=10, z_price_return=-10)
    states[0].raw_metrics.pb = 0.1

    candidate = _candidate(discover_opportunities(states, ResearchMandate(preset=PresetName.VALUE, top_k=100)), "C0")
    evaluation = candidate.lens_evaluations[LensName.DISLOCATION]
    assert evaluation.score is None
    assert evaluation.status == "not_evaluable"
    assert candidate.discrepancy is None
    assert candidate.discrepancy_label == "NOT_EVALUABLE"


def test_standard_and_exploratory_cohort_rules_are_distinct() -> None:
    states = _eight_complete()[:3]
    standard = DiscoveryEngine()._evaluate_all(states, EvidenceStandard.STANDARD)
    exploratory = DiscoveryEngine()._evaluate_all(states, EvidenceStandard.EXPLORATORY)

    assert standard["C2"][LensName.VALUE].cohort_size == 3
    assert standard["C2"][LensName.VALUE].status == "low_sample"
    assert standard["C2"][LensName.VALUE].usable is False
    assert exploratory["C2"][LensName.VALUE].usable is True
    assert exploratory["C2"][LensName.VALUE].reasons[-1] == "low_sample" or "low_sample" in exploratory["C2"][LensName.VALUE].reasons

    two = _eight_complete()[:2]
    insufficient = DiscoveryEngine()._evaluate_all(two, EvidenceStandard.EXPLORATORY)
    assert insufficient["C1"][LensName.VALUE].status == "insufficient_cohort"
    assert insufficient["C1"][LensName.VALUE].score is None


def test_permutation_and_display_mode_do_not_change_scores_or_order() -> None:
    states = _eight_complete()
    mandate = _custom(dislocation=40, growth=30, profitability=30, value=0)
    advanced = mandate.model_copy(update={"display_mode": DisplayMode.ADVANCED})
    original = discover_opportunities(states, mandate)
    reversed_input = discover_opportunities(list(reversed(states)), advanced)

    assert [c.symbol for c in original.candidates] == [c.symbol for c in reversed_input.candidates]
    assert [c.research_fit for c in original.candidates] == pytest.approx(
        [c.research_fit for c in reversed_input.candidates]
    )


def test_investor_presets_can_rank_same_ground_truth_differently() -> None:
    states = _eight_complete()
    # A has the strongest discrepancy but modest operating profitability.
    states[0].symbol = "A"
    states[0].peer_z = PeerZScores(z_revenue_growth=5, z_earnings_growth=5, z_margin_change=5, z_price_return=-5)
    states[0].raw_metrics.operating_margin = 0.01
    states[0].raw_metrics.margin_change = 0.001
    # B is very profitable but has a poor discrepancy.
    states[1].symbol = "B"
    # Keep D just above the admission threshold so both names participate in
    # the dislocation result; its percentile is nevertheless far below A.
    states[1].peer_z = PeerZScores(z_revenue_growth=1, z_earnings_growth=1, z_margin_change=1, z_price_return=-0.1)
    states[1].raw_metrics.operating_margin = 0.90
    states[1].raw_metrics.margin_change = 0.30

    dislocation = discover_opportunities(states, ResearchMandate(preset=PresetName.DISLOCATION, top_k=100))
    profitability = discover_opportunities(states, ResearchMandate(preset=PresetName.PROFITABILITY, top_k=100))
    dislocation_order = [candidate.symbol for candidate in dislocation.candidates]
    profitability_order = [candidate.symbol for candidate in profitability.candidates]

    assert dislocation_order.index("A") < dislocation_order.index("B")
    assert profitability_order.index("B") < profitability_order.index("A")


def test_active_missing_lens_excludes_while_zero_weight_lens_does_not() -> None:
    states = _eight_complete()
    gap = states[0]
    gap.symbol = "GAP"
    gap.peer_z = PeerZScores(z_revenue_growth=6, z_earnings_growth=6, z_margin_change=6, z_price_return=-6)
    gap.raw_metrics.revenue_growth = None
    gap.raw_metrics.earnings_growth = None

    dislocation = discover_opportunities(states, ResearchMandate(preset=PresetName.DISLOCATION, top_k=100))
    growth = discover_opportunities(states, ResearchMandate(preset=PresetName.GROWTH, top_k=100))

    assert "GAP" in [candidate.symbol for candidate in dislocation.candidates]
    assert "GAP" not in [candidate.symbol for candidate in growth.candidates]
    assert growth.exclusions["active_lens_unavailable:growth"] >= 1


def test_filters_do_not_recompute_remaining_reference_scores() -> None:
    states = _eight_complete()
    broad = discover_opportunities(states, ResearchMandate(preset=PresetName.VALUE, top_k=100))
    narrowed = discover_opportunities(
        states,
        ResearchMandate(
            preset=PresetName.VALUE,
            filters=MandateFilters(include_symbols=("C7",)),
            top_k=100,
        ),
    )

    before = _candidate(broad, "C7").lens_evaluations[LensName.VALUE].score
    after = _candidate(narrowed, "C7").lens_evaluations[LensName.VALUE].score
    assert before == pytest.approx(after)
    assert narrowed.funnel.passed_filters == 1


def test_invalid_weights_are_rejected_at_the_contract_boundary() -> None:
    with pytest.raises(ValidationError):
        LensWeights(dislocation=-1)
    with pytest.raises(ValidationError):
        LensWeights(dislocation=0, growth=0, profitability=0, value=0)
    with pytest.raises(ValidationError):
        LensWeights(dislocation=math.inf)
    with pytest.raises(ValidationError):
        ResearchMandate(preset=PresetName.CUSTOM)


def test_subsector_cap_is_applied_after_global_rank_and_never_relaxed() -> None:
    alpha = _eight_complete("alpha")
    beta = _eight_complete("beta")
    for index, state in enumerate(alpha):
        state.symbol = f"A{index}"
    for index, state in enumerate(beta):
        state.symbol = f"B{index}"
    result = discover_opportunities(
        alpha + beta,
        ResearchMandate(preset=PresetName.DISLOCATION, max_per_subsector=1, top_k=3),
    )

    assert len(result.candidates) == 2
    assert {candidate.subsector for candidate in result.candidates} == {"alpha", "beta"}
    assert result.funnel.after_subsector_limit == 2
    assert result.exclusions["subsector_limit"] > 0


def test_candidate_exposes_numeric_evidence_and_mandate_transparency() -> None:
    result = discover_opportunities(_eight_complete(), _custom(dislocation=50, growth=50, profitability=0, value=0))
    candidate = _candidate(result, "C7")

    assert result.effective_weights[LensName.DISLOCATION] == pytest.approx(0.5)
    assert result.effective_weights[LensName.GROWTH] == pytest.approx(0.5)
    assert candidate.weighted_contributions[LensName.DISLOCATION] > 0
    assert candidate.weighted_contributions[LensName.GROWTH] > 0
    assert any("score=" in item and "contribution=" in item for item in candidate.evidence)
    assert candidate.lens_evaluations[LensName.DISLOCATION].inputs["discrepancy"] == pytest.approx(candidate.discrepancy)


def test_inclusive_numeric_filters_and_missing_metrics_have_explicit_outcomes() -> None:
    states = _eight_complete()
    # The exact inclusive boundary passes; a missing value with an active
    # range is excluded with an auditable reason.
    boundary = states[-1].raw_metrics.revenue_growth
    passing = discover_opportunities(
        states,
        ResearchMandate(
            preset=PresetName.DISLOCATION,
            filters=MandateFilters(revenue_growth=NumericRange(minimum=boundary, maximum=boundary)),
            top_k=100,
        ),
    )
    assert [candidate.symbol for candidate in passing.candidates] == ["C7"]

    states[-1].raw_metrics.revenue_growth = None
    missing = discover_opportunities(
        states,
        ResearchMandate(
            preset=PresetName.DISLOCATION,
            filters=MandateFilters(revenue_growth=NumericRange(minimum=0)),
            top_k=100,
        ),
    )
    assert missing.exclusions["missing_filter_metric:revenue_growth"] >= 1
