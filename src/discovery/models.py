"""Public contracts for the deterministic Day 3 discovery domain.

The request-facing models intentionally accept only structured filters. They
never accept expressions or formulas to execute. Result models preserve the
numeric inputs and reasons needed to audit a ranking.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LensName(StrEnum):
    DISLOCATION = "dislocation"
    GROWTH = "growth"
    PROFITABILITY = "profitability"
    VALUE = "value"


class PresetName(StrEnum):
    DISLOCATION = "dislocation"
    GROWTH = "growth"
    PROFITABILITY = "profitability"
    VALUE = "value"
    CUSTOM = "custom"


class EvidenceStandard(StrEnum):
    STANDARD = "standard"
    EXPLORATORY = "exploratory"


class DisplayMode(StrEnum):
    GUIDED = "guided"
    ADVANCED = "advanced"


class NumericRange(BaseModel):
    """Inclusive lower/upper bound for one numeric metric."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> NumericRange:
        for value in (self.minimum, self.maximum):
            if value is not None and not math.isfinite(value):
                raise ValueError("range bounds must be finite")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must be less than or equal to maximum")
        return self

    def contains(self, value: float) -> bool:
        return (self.minimum is None or value >= self.minimum) and (
            self.maximum is None or value <= self.maximum
        )


class LensWeights(BaseModel):
    """Unnormalised non-negative weights sent on the 0--100 scale."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dislocation: Annotated[float, Field(ge=0, le=100)] = 100
    growth: Annotated[float, Field(ge=0, le=100)] = 0
    profitability: Annotated[float, Field(ge=0, le=100)] = 0
    value: Annotated[float, Field(ge=0, le=100)] = 0

    @model_validator(mode="after")
    def validate_values(self) -> LensWeights:
        values = self.as_dict().values()
        if any(not math.isfinite(value) for value in values):
            raise ValueError("weights must be finite")
        if sum(values) <= 0:
            raise ValueError("at least one lens weight must be positive")
        return self

    def as_dict(self) -> dict[LensName, float]:
        return {lens: float(getattr(self, lens.value)) for lens in LensName}

    def normalized(self) -> dict[LensName, float]:
        values = self.as_dict()
        total = sum(values.values())
        return {lens: value / total for lens, value in values.items()}


PRESET_WEIGHTS: dict[PresetName, LensWeights] = {
    PresetName.DISLOCATION: LensWeights(dislocation=100, growth=0, profitability=0, value=0),
    PresetName.GROWTH: LensWeights(dislocation=20, growth=60, profitability=20, value=0),
    PresetName.PROFITABILITY: LensWeights(dislocation=20, growth=20, profitability=60, value=0),
    PresetName.VALUE: LensWeights(dislocation=0, growth=0, profitability=30, value=70),
}


class MandateFilters(BaseModel):
    """Structured universe and raw-metric constraints.

    List membership is OR within a list and AND across filters; exclusion wins.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    include_sectors: tuple[str, ...] = ()
    exclude_sectors: tuple[str, ...] = ()
    include_subsectors: tuple[str, ...] = ()
    exclude_subsectors: tuple[str, ...] = ()
    include_symbols: tuple[str, ...] = ()
    exclude_symbols: tuple[str, ...] = ()
    revenue_growth: NumericRange | None = None
    earnings_growth: NumericRange | None = None
    operating_margin: NumericRange | None = None
    margin_change: NumericRange | None = None
    pb: NumericRange | None = None
    price_return: NumericRange | None = None
    market_cap: NumericRange | None = None
    transaction_activity: NumericRange | None = None
    price_age_days: NumericRange | None = None
    financial_age_days: NumericRange | None = None

    @model_validator(mode="after")
    def validate_lists(self) -> MandateFilters:
        for name in (
            "include_sectors", "exclude_sectors", "include_subsectors",
            "exclude_subsectors", "include_symbols", "exclude_symbols",
        ):
            if any(not value.strip() for value in getattr(self, name)):
                raise ValueError(f"{name} cannot contain blank values")
        return self


class ResearchMandate(BaseModel):
    """Versioned search mandate accepted by the discovery service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = "v1"
    preset: PresetName = PresetName.DISLOCATION
    weights: LensWeights | None = None
    filters: MandateFilters = Field(default_factory=MandateFilters)
    evidence_standard: EvidenceStandard = EvidenceStandard.STANDARD
    top_k: Annotated[int, Field(ge=1, le=100)] = 10
    max_per_subsector: Annotated[int | None, Field(ge=1, le=100)] = None
    display_mode: DisplayMode = DisplayMode.GUIDED

    @model_validator(mode="after")
    def validate_preset(self) -> ResearchMandate:
        if self.preset == PresetName.CUSTOM:
            if self.weights is None:
                raise ValueError("custom preset requires weights")
            return self
        expected = PRESET_WEIGHTS[self.preset]
        if self.weights is not None and self.weights != expected:
            raise ValueError("non-custom presets require their fixed weights")
        return self

    @property
    def effective_weights(self) -> LensWeights:
        return self.weights if self.preset == PresetName.CUSTOM else PRESET_WEIGHTS[self.preset]

    @property
    def normalized_weights(self) -> dict[LensName, float]:
        return self.effective_weights.normalized()


class LensEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lens: LensName
    score: float | None = None
    matched: bool = False
    usable: bool = False
    status: str
    cohort_size: int = 0
    period: str | None = None
    inputs: dict[str, float] = Field(default_factory=dict)
    reasons: tuple[str, ...] = ()


class LensCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lens: LensName
    evaluated: int = 0
    usable_standard: int = 0
    usable_exploratory: int = 0
    matched: int = 0
    cohorts: dict[str, int] = Field(default_factory=dict)


class FilterFunnel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total: int
    passed_filters: int
    passed_active_lenses: int
    matched_an_active_lens: int
    after_subsector_limit: int
    returned: int
    excluded: dict[str, int] = Field(default_factory=dict)


class OpportunityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    company_name: str | None = None
    sector: str
    subsector: str
    research_fit: float
    rank_before_subsector_limit: int
    rank: int
    weighted_contributions: dict[LensName, float]
    matched_lenses: tuple[LensName, ...]
    lens_evaluations: dict[LensName, LensEvaluation]
    discrepancy: float | None = None
    discrepancy_label: str = "NOT_EVALUABLE"
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class DiscoveryResult(BaseModel):
    """Result of one snapshot/mandate search; no network state is retained."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mandate: ResearchMandate
    effective_weights: dict[LensName, float]
    snapshot_date: str | None = None
    candidates: tuple[OpportunityCandidate, ...] = ()
    coverage: dict[LensName, LensCoverage]
    funnel: FilterFunnel
    exclusions: dict[str, int] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()
