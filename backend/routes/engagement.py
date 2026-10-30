"""
WorkforceIQ – Engagement Analytics Routes.

Endpoints:
  GET /api/v1/engagement/trends  – Longitudinal engagement and sentiment trends
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.engagement import EngagementTrend
from backend.services.analytics_service import get_engagement_trends

router = APIRouter(prefix="/api/v1/engagement", tags=["Engagement Analytics"])


@router.get(
    "/trends",
    response_model=EngagementTrend,
    summary="Engagement longitudinal trends",
    description=(
        "Returns survey-based longitudinal engagement metrics including job satisfaction, "
        "work-life balance, management trust, career growth opportunities, "
        "burnout risk index, and sentiment score. "
        "Missing survey data is preserved as NULL (not treated as negative). "
        "Supports optional department and date range filters."
    ),
)
def engagement_trends(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    start_date: Optional[date] = Query(None, description="Start date for trend analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for trend analysis (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
):
    return get_engagement_trends(
        session,
        department_id=department_id,
        start_date=start_date,
        end_date=end_date,
    )
