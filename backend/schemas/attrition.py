"""
Pydantic schemas for Operational Attrition Risk Intelligence and Historical Analytics.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskTierBreakdown(BaseModel):
    tier: str  # LOW, MEDIUM, HIGH, CRITICAL
    employee_count: int
    percentage: float
    avg_flight_risk: float


class DepartmentAttritionMetric(BaseModel):
    department_id: str
    department_name: str
    active_headcount: int
    high_critical_risk_count: int
    high_critical_risk_pct: float
    historical_separations_count: int
    historical_voluntary_rate: float


class AttritionSummary(BaseModel):
    """Operational workforce retention risk overview."""
    total_active_workforce: int
    overall_attrition_risk_avg: float
    high_risk_count: int
    critical_risk_count: int
    retention_risk_breakdown: List[RiskTierBreakdown] = Field(default_factory=list)
    department_risk_breakdown: List[DepartmentAttritionMetric] = Field(default_factory=list)
    top_workforce_flight_drivers: List[Dict[str, float]] = Field(default_factory=list)


class HistoricalSeparationPoint(BaseModel):
    month_year: str
    voluntary_separations: int
    involuntary_separations: int
    retirements: int
    total_separations: int
    voluntary_attrition_rate: float


class AttritionTrend(BaseModel):
    """Historical longitudinal separation trends (restricted HR access)."""
    analysis_window_months: int
    total_historical_separations: int
    overall_voluntary_attrition_rate: float
    regrettable_loss_rate: float
    monthly_trends: List[HistoricalSeparationPoint] = Field(default_factory=list)
