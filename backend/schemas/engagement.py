"""
Pydantic schemas for Engagement Surveys and Longitudinal Analytics.
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EngagementRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    survey_id: str
    employee_id: str
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    survey_date: date
    enps_score: Optional[int] = Field(None, ge=0, le=10)
    job_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    work_life_balance: Optional[int] = Field(None, ge=1, le=5)
    management_trust: Optional[int] = Field(None, ge=1, le=5)
    career_growth_opps: Optional[int] = Field(None, ge=1, le=5)
    burnout_risk_index: Optional[float] = Field(None, ge=0.0, le=1.0)
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    is_missing: bool = False  # Explicit flag to protect missing neutrality


class EngagementTrendPoint(BaseModel):
    survey_date: date
    response_count: int
    completion_rate_pct: float
    avg_job_satisfaction: Optional[float] = None
    avg_work_life_balance: Optional[float] = None
    avg_management_trust: Optional[float] = None
    avg_career_growth_opps: Optional[float] = None
    avg_burnout_risk: Optional[float] = None
    avg_sentiment: Optional[float] = None


class EngagementTrend(BaseModel):
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    total_surveys_analyzed: int
    overall_avg_satisfaction: Optional[float] = None
    overall_avg_burnout: Optional[float] = None
    trend_points: List[EngagementTrendPoint] = Field(default_factory=list)
