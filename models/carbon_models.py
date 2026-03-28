"""
Pydantic v2 models for the Carbon Market Intelligence Report JSON schema.
All fields use 'missing' as the sentinel value for unavailable data.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class LatestPrice(BaseModel):
    value: str = "missing"
    currency: str = "missing"
    unit: str = "per tCO2e"


class MarketOverview(BaseModel):
    market_type: str = "missing"
    region: str = "missing"
    latest_price: LatestPrice = Field(default_factory=LatestPrice)
    price_trend: str = "missing"
    volatility: str = "missing"
    performance_rating: str = "missing"
    color_code: str = "Yellow"
    key_drivers: List[str] = Field(default_factory=list)
    insight: str = "missing"


class ComplianceMarket(BaseModel):
    market_name: str = "missing"
    region: str = "missing"
    price: str = "missing"
    currency: str = "missing"
    trend: str = "missing"
    performance: str = "missing"
    color_code: str = "Yellow"
    regulatory_updates: str = "missing"
    insight: str = "missing"


class VoluntaryCarbonMarket(BaseModel):
    average_price: str = "missing"
    currency: str = "USD"
    price_range: str = "missing"
    demand_trend: str = "missing"
    supply_trend: str = "missing"
    market_condition: str = "missing"
    color_code: str = "Yellow"
    key_standards: List[str] = Field(default_factory=list)
    insight: str = "missing"


class CarbonOffset(BaseModel):
    project_type: str = "missing"
    region: str = "missing"
    standard: str = "missing"
    price_range: str = "missing"
    currency: str = "USD"
    quality_assessment: str = "missing"
    color_code: str = "Yellow"
    additionality: str = "missing"
    permanence: str = "missing"
    risks: List[str] = Field(default_factory=list)
    insight: str = "missing"


class PolicyAndRegulation(BaseModel):
    recent_updates: List[str] = Field(default_factory=list)
    carbon_tax: str = "missing"
    ets_changes: str = "missing"
    policy_risk_level: str = "missing"
    insight: str = "missing"


class RiskAnalysis(BaseModel):
    market_risks: List[str] = Field(default_factory=list)
    pricing_risks: List[str] = Field(default_factory=list)
    policy_risks: List[str] = Field(default_factory=list)
    overall_risk_level: str = "missing"
    color_code: str = "Yellow"
    insight: str = "missing"


class OpportunityAnalysis(BaseModel):
    investment_opportunities: List[str] = Field(default_factory=list)
    corporate_strategy_opportunities: List[str] = Field(default_factory=list)
    esg_opportunities: List[str] = Field(default_factory=list)
    insight: str = "missing"


class Forecast(BaseModel):
    short_term_outlook: str = "missing"
    long_term_outlook: str = "missing"
    price_direction: str = "missing"
    price_target_short_term: str = "missing"
    price_target_long_term: str = "missing"
    confidence: str = "missing"
    insight: str = "missing"


class ExcelAnalysisRow(BaseModel):
    sheet: str = "Carbon Dashboard"
    metric: str = "missing"
    value: str = "missing"
    unit: str = "missing"
    performance: str = "missing"
    color_code: str = "Yellow"


class WordReport(BaseModel):
    title: str = "Carbon Market Intelligence Report"
    date: str = "missing"
    executive_summary: str = "missing"
    market_overview_section: str = "missing"
    pricing_analysis_section: str = "missing"
    offsets_analysis_section: str = "missing"
    policy_section: str = "missing"
    risk_section: str = "missing"
    opportunity_section: str = "missing"
    forecast_section: str = "missing"
    conclusion: str = "missing"
    strategic_recommendations: List[str] = Field(default_factory=list)


class DataQuality(BaseModel):
    confidence: str = "missing"
    data_freshness: str = "missing"
    missing_information: List[str] = Field(default_factory=list)
    notes: str = "missing"


class SourceReference(BaseModel):
    topic: str = "missing"
    snippet: str = "missing"
    source: str = "missing"


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------

class CarbonIntelligenceReport(BaseModel):
    """Root model representing the full Carbon Market Intelligence Report."""

    market_overview: MarketOverview = Field(default_factory=MarketOverview)
    compliance_markets: List[ComplianceMarket] = Field(default_factory=list)
    voluntary_carbon_market: VoluntaryCarbonMarket = Field(
        default_factory=VoluntaryCarbonMarket
    )
    carbon_offsets: List[CarbonOffset] = Field(default_factory=list)
    policy_and_regulation: PolicyAndRegulation = Field(
        default_factory=PolicyAndRegulation
    )
    risk_analysis: RiskAnalysis = Field(default_factory=RiskAnalysis)
    opportunity_analysis: OpportunityAnalysis = Field(
        default_factory=OpportunityAnalysis
    )
    forecast: Forecast = Field(default_factory=Forecast)
    excel_analysis: List[ExcelAnalysisRow] = Field(default_factory=list)
    word_report: WordReport = Field(default_factory=WordReport)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    source_references: List[SourceReference] = Field(default_factory=list)

    def color_to_hex(self, color_code: str) -> str:
        """Map color_code string to hex for Excel/Word formatting."""
        mapping = {
            "Green": "00B050",
            "Yellow": "FFFF00",
            "Red": "FF0000",
        }
        return mapping.get(color_code, "FFFF00")
