"""Pydantic data models for Sectors API v2 responses.

Refined against live Sectors API responses.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base model with relaxed extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# 1. Taxonomy & Screener
class SubsectorInfo(APIModel):
    sector: str
    subsector: str | None = None
    sub_sectors: list[str] = Field(default_factory=list)


class CompanyItem(APIModel):
    symbol: str
    company_name: str | None = None


class CompaniesResponse(APIModel):
    results: list[CompanyItem] = Field(default_factory=list)
    pagination: dict[str, Any] = Field(default_factory=dict)


# 2. Financials (Quarterly)
class QuarterlyFinancial(APIModel):
    symbol: str | None = None
    date: str | None = None
    revenue: float | None = None
    operating_pnl: float | None = None
    earnings: float | None = None
    gross_profit: float | None = None
    cost_of_revenue: float | None = None
    total_equity: float | None = None
    total_assets: float | None = None
    total_debt: float | None = None
    ebit: float | None = None
    ebitda: float | None = None


# 3. Daily Transactions & Price
class DailyTransaction(APIModel):
    date: str
    close: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    change: float | None = None


# 4. News, Filings & Corporate Actions (Mosaic Linguistic Layer)
class FilingItem(APIModel):
    id: Any | None = None
    symbol: str | None = None
    date: str | None = None
    title: str | None = None
    category: str | None = None
    description: str | None = None
    url: str | None = None


class CorporateActionItem(APIModel):
    action_type: str | None = None
    date: str | None = None
    description: str | None = None
    details: dict[str, Any] | None = None


class NewsItem(APIModel):
    id: Any | None = None
    title: str | None = None
    date: str | None = None
    url: str | None = None
    source: str | None = None
    summary: str | None = None


# 5. Foreign Flow (Confirmation Layer)
class ForeignFlowItem(APIModel):
    date: str
    net_foreign_inflow: float | None = None


class ForeignFlowResponse(APIModel):
    symbol: str
    start: str | None = None
    end: str | None = None
    data: list[ForeignFlowItem] = Field(default_factory=list)
