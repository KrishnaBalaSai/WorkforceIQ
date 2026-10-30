"""
WorkforceIQ – Department and Job Role Routes.

Endpoints:
  GET /api/v1/departments                           – All departments with aggregated metrics
  GET /api/v1/departments/{department_id}           – Single department detail
  GET /api/v1/roles                                 – All job roles (optional dept filter)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.roles import DepartmentSummary, RoleSummary
from backend.services.department_service import get_department_detail, get_departments, get_roles

router = APIRouter(tags=["Departments & Roles"])


@router.get(
    "/api/v1/departments",
    response_model=List[DepartmentSummary],
    summary="List all departments",
    description=(
        "Returns all departments with aggregated workforce metrics: headcount, average salary, "
        "engagement satisfaction, and retention risk distribution."
    ),
)
def list_departments(session: Session = Depends(get_session)):
    return get_departments(session)


@router.get(
    "/api/v1/departments/{department_id}",
    response_model=DepartmentSummary,
    summary="Single department detail",
    description="Returns aggregated workforce metrics for a specific department.",
)
def get_department(department_id: str, session: Session = Depends(get_session)):
    dept = get_department_detail(session, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{department_id}' not found.")
    return dept


@router.get(
    "/api/v1/roles",
    response_model=List[RoleSummary],
    summary="List job roles",
    description=(
        "Returns all job roles with grade band, compensation range, and active headcount. "
        "Filter by department_id to see roles within a specific organizational unit."
    ),
)
def list_roles(
    department_id: Optional[str] = Query(None, description="Filter roles by department ID"),
    session: Session = Depends(get_session),
):
    return get_roles(session, department_id=department_id)
