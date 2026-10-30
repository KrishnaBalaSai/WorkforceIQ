"""
WorkforceIQ – Data Validation and Anomaly Routes.

Endpoints:
  GET /api/v1/validation/summary     – 12-pillar validation summary
  GET /api/v1/validation/anomalies   – Paginated data anomaly registry
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.common import PaginatedResponse
from backend.schemas.validation import ValidationSummaryResponse
from backend.services.validation_service import get_anomalies, get_validation_summary

router = APIRouter(prefix="/api/v1/validation", tags=["Data Validation"])


@router.get(
    "/summary",
    response_model=ValidationSummaryResponse,
    summary="12-pillar data validation summary",
    description=(
        "Returns the enterprise data quality validation summary across all 12 validation pillars: "
        "primary-key uniqueness, foreign-key integrity, enum validation, date ordering, "
        "effective-date consistency, duplicate detection, arithmetic reconciliation, "
        "lifecycle transitions, missing-value handling, attrition consistency, "
        "temporal leakage detection, and cross-entity join validity."
    ),
)
def validation_summary():
    return get_validation_summary()


@router.get(
    "/anomalies",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="Paginated data anomaly registry",
    description=(
        "Returns paginated data quality anomalies tracked in the system anomaly registry. "
        "Supports filtering by anomaly type, severity, and resolution status."
    ),
)
def list_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    session: Session = Depends(get_session),
):
    return get_anomalies(
        session,
        page=page,
        page_size=page_size,
        anomaly_type=anomaly_type,
        severity=severity,
        is_resolved=is_resolved,
    )
