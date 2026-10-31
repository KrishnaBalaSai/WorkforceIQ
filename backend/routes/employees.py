
"""
WorkforceIQ – Employee Routes.

Endpoints:
  GET  /api/v1/employees                 – Paginated employee directory
  GET  /api/v1/employees/{employee_id}   – Employee 360 profile
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.common import PaginatedResponse
from backend.schemas.employees import EmployeeDetail, EmployeeSummary
from backend.services.employee_service import get_employee_detail, get_employees

router = APIRouter(prefix="/api/v1/employees", tags=["Employees"])


@router.get(
    "",
    response_model=PaginatedResponse[EmployeeSummary],
    summary="List employees",
    description=(
        "Returns a paginated, filtered, and sortable list of employees. "
        "Supports search by name, email, or employee ID. "
        "Risk tier and operational risk probability filters use the latest "
        "synthetic workforce risk scores."
    ),
)
def list_employees(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Records per page"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    role_id: Optional[str] = Query(None, description="Filter by job role ID"),
    status: Optional[str] = Query(
        None,
        description="Filter by employment status (ACTIVE, ON_LEAVE, TERMINATED)",
    ),
    work_location: Optional[str] = Query(
        None,
        description="Filter by work location (REMOTE, ONSITE, HYBRID)",
    ),
    risk_tier: Optional[str] = Query(
        None,
        description="Filter by latest operational risk tier",
    ),
    min_risk_probability: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum operational risk probability",
    ),
    max_risk_probability: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Maximum operational risk probability",
    ),
    search: Optional[str] = Query(
        None,
        min_length=2,
        description="Full-text search: employee ID, name, or email",
    ),
    sort_by: str = Query("employee_id", description="Sort column"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort direction",
    ),
    session: Session = Depends(get_session),
):
    if (
        min_risk_probability is not None
        and max_risk_probability is not None
        and min_risk_probability > max_risk_probability
    ):
        raise HTTPException(
            status_code=422,
            detail="Minimum risk probability cannot exceed maximum risk probability.",
        )

    return get_employees(
        session,
        page=page,
        page_size=page_size,
        department_id=department_id,
        role_id=role_id,
        status=status,
        work_location=work_location,
        search=search,
        risk_tier=risk_tier,
        min_risk_probability=min_risk_probability,
        max_risk_probability=max_risk_probability,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeDetail,
    summary="Employee 360 profile",
    description=(
        "Returns the complete longitudinal profile for a single employee including: "
        "compensation history, performance evaluations, engagement surveys, "
        "project assignments, time-off records, skills, and latest retention risk intelligence."
    ),
)
def get_employee(
    employee_id: str,
    session: Session = Depends(get_session),
):
    profile = get_employee_detail(session, employee_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Employee '{employee_id}' not found.",
        )
    return profile
