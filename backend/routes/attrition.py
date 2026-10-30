"""
WorkforceIQ – Attrition Intelligence Routes.

Endpoints:
  GET /api/v1/attrition/summary          – Operational workforce flight-risk summary
  GET /api/v1/attrition/trends           – Historical monthly separation trends (restricted)
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.attrition import AttritionSummary, AttritionTrend
from backend.services.analytics_service import (
    get_historical_attrition_trends,
    get_operational_attrition_summary,
)

router = APIRouter(prefix="/api/v1/attrition", tags=["Attrition Intelligence"])


@router.get(
    "/summary",
    response_model=AttritionSummary,
    summary="Operational attrition risk summary",
    description=(
        "Returns real-time operational workforce flight-risk distribution derived exclusively "
        "from ML prediction scores. Does NOT expose ground-truth exit outcomes. "
        "Safe for standard operational dashboards."
    ),
)
def attrition_summary(session: Session = Depends(get_session)):
    return get_operational_attrition_summary(session)


@router.get(
    "/trends",
    response_model=AttritionTrend,
    summary="Historical separation trends (HR restricted)",
    description=(
        "**Restricted endpoint.** Returns monthly voluntary, involuntary, and regrettable "
        "separation counts from historical exit records. "
        "Requires the `X-HR-Authorization: true` header for access. "
        "Exit outcome data is strictly isolated from ML prediction features."
    ),
)
def attrition_trends(
    x_hr_authorization: str = Header(
        default="false",
        alias="X-HR-Authorization",
        description="Set to 'true' to access restricted historical separation data.",
    ),
    session: Session = Depends(get_session),
):
    is_authorized = x_hr_authorization.lower() == "true"
    if not is_authorized:
        raise HTTPException(
            status_code=403,
            detail=(
                "Access denied. Historical separation outcome data requires "
                "HR Analytics authorization. Set header X-HR-Authorization: true."
            ),
        )
    try:
        return get_historical_attrition_trends(session, is_authorized=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
