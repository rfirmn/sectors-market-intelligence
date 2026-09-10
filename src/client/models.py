"""Pydantic data models for Sectors API responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base model with relaxed extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# 1. Taxonomy & Screener
class SubsectorInfo(APIModel):
    sector: str
    sub_sectors: list[str] = Field(default_factory=list)


class CompanyOverview(APIModel):
    symbol: str
    company_name: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    market_cap: float | None = None
    pe: float | None = None
    pb: float | None = None
    close: float | None = None


# 2. Financials (Quarterly)
class QuarterlyFinancial(APIModel):
    year: int | None = None
    quarter: int | None = None
    period: str | None = None
    revenue: float | None = None
    earnings: float | None = None
    operating_profit: float | None = None
    gross_profit: float | None = None
    total_equity: float | None = None
    total_assets: float | None = None


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


# 5. Foreign Flow & Broker Summary (Confirmation Layer)
class ForeignFlowItem(APIModel):
    date: str | None = None
    foreign_buy: float | None = None
    foreign_sell: float | None = None
    net_foreign: float | None = None
