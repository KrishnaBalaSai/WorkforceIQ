"""
Pydantic schemas for Job Roles and Departments.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: str
    department_id: str
    department_name: Optional[str] = None
    title: str
    grade_level: int = Field(ge=1, le=15)
    min_salary: float = Field(ge=0.0)
    mid_salary: float = Field(ge=0.0)
    max_salary: float = Field(ge=0.0)
    is_exempt: bool
    active_headcount: Optional[int] = 0


class DepartmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department_id: str
    name: str
    division: str
    cost_center_code: str
    head_employee_id: Optional[str] = None
    head_name: Optional[str] = None
    annual_budget: float = Field(ge=0.0)
    total_headcount: Optional[int] = 0
    active_headcount: Optional[int] = 0
    attrited_headcount: Optional[int] = 0
    average_salary: Optional[float] = None
    average_compa_ratio: Optional[float] = None
    average_engagement: Optional[float] = None
    high_risk_count: Optional[int] = 0
