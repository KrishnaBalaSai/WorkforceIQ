"""
Pydantic schemas for Employee entities.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DepartmentMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department_id: str
    name: str
    division: str


class RoleMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role_id: str
    title: str
    grade_level: int
    is_exempt: bool


class ManagerMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: str
    first_name: str
    last_name: str
    email: str


class EmployeeSummary(BaseModel):
    """Compact summary schema for employee directory and paginated tables."""
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    first_name: str
    last_name: str
    email: str
    department_id: str
    department_name: Optional[str] = None
    role_id: str
    role_title: Optional[str] = None
    manager_id: Optional[str] = None
    status: str
    employment_type: str
    work_location: str
    hire_date: date
    probation_end_date: Optional[date] = None
    is_active: bool
    latest_flight_risk: Optional[float] = None
    latest_risk_tier: Optional[str] = None


class CompensationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    compensation_id: str
    base_salary: float
    bonus_target_pct: float
    stock_options_granted: int
    currency: str
    effective_from: date
    effective_to: Optional[date] = None
    is_current: bool
    revision_reason: str


class PerformanceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evaluation_id: str
    evaluation_cycle: str
    rating: str
    numeric_score: float
    goals_met_pct: float
    promotion_readiness: str
    feedback_summary: Optional[str] = None
    evaluation_date: date


class EngagementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    survey_id: str
    survey_date: date
    enps_score: int
    job_satisfaction: int
    work_life_balance: int
    management_trust: int
    career_growth_opps: int
    burnout_risk_index: float
    sentiment_score: float


class ProjectAssignmentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assignment_id: str
    project_id: str
    project_name: Optional[str] = None
    role_in_project: str
    allocation_pct: float
    logged_hours_weekly: float
    start_date: date
    end_date: Optional[date] = None


class TimeOffItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leave_id: str
    leave_type: str
    start_date: date
    end_date: date
    is_approved: bool
    total_days: int


class SkillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    skill_id: str
    skill_name: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: int
    certified_flag: bool


class EmployeeDetail(BaseModel):
    """Full Employee 360 profile with longitudinal relationships."""
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    first_name: str
    last_name: str
    email: str
    department_id: str
    department: Optional[DepartmentMini] = None
    role_id: str
    role: Optional[RoleMini] = None
    manager_id: Optional[str] = None
    manager: Optional[ManagerMini] = None
    status: str
    employment_type: str
    work_location: str
    hire_date: date
    probation_end_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Longitudinal profiles
    skills: List[SkillItem] = Field(default_factory=list)
    compensation_history: List[CompensationItem] = Field(default_factory=list)
    performance_evaluations: List[PerformanceItem] = Field(default_factory=list)
    engagement_surveys: List[EngagementItem] = Field(default_factory=list)
    project_assignments: List[ProjectAssignmentItem] = Field(default_factory=list)
    time_off_records: List[TimeOffItem] = Field(default_factory=list)

    # Operational retention risk intelligence
    latest_flight_risk: Optional[float] = None
    latest_risk_tier: Optional[str] = None
    latest_risk_drivers: List[str] = Field(default_factory=list)
