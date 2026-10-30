"""
WorkforceIQ – Workload Analytics Routes.

Endpoints:
  GET /api/v1/workload/analytics  – Workload distribution and over-allocation metrics
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.workload import WorkloadTrend
from backend.services.analytics_service import get_workload_analytics

router = APIRouter(prefix="/api/v1/workload", tags=["Workload Analytics"])


@router.get(
    "/analytics",
    response_model=WorkloadTrend,
    summary="Workload distribution analytics",
    description=(
        "Returns workforce workload metrics including total active projects, "
        "assigned employee counts, average weekly hours, and over-allocation percentage "
        "(employees logging >45 hours/week). Supports department and date range filters."
    ),
)
def workload_analytics(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    start_date: Optional[date] = Query(None, description="Filter assignments starting from date"),
    end_date: Optional[date] = Query(None, description="Filter assignments ending before date"),
    session: Session = Depends(get_session),
):
    return get_workload_analytics(
        session,
        department_id=department_id,
        start_date=start_date,
        end_date=end_date,
    )
