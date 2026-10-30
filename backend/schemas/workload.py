"""
Pydantic schemas for Workload and Project Assignment Analytics.
"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkloadRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: str
    employee_id: str
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    project_id: str
    project_name: str
    role_in_project: str
    allocation_pct: float
    logged_hours_weekly: float
    start_date: date
    end_date: Optional[date] = None
    is_overallocated: bool = False


class WorkloadTrendPoint(BaseModel):
    period: str
    active_assignments: int
    avg_logged_hours_weekly: float
    overallocated_employees_count: int
    burnout_risk_correlation: Optional[float] = None


class WorkloadTrend(BaseModel):
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    total_active_projects: int
    total_assigned_employees: int
    average_weekly_hours: float
    overallocated_percentage: float
    trends: List[WorkloadTrendPoint] = Field(default_factory=list)
