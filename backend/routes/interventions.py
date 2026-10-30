r"""
WorkforceIQ – Retention Intervention Routes.

Human-in-the-Loop lifecycle:
  CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
                                                       \-> CANCELLED

Endpoints:
  GET    /api/v1/interventions                       – Paginated interventions list
  POST   /api/v1/interventions                       – Propose new intervention
  GET    /api/v1/interventions/{intervention_id}     – Single intervention detail
  PATCH  /api/v1/interventions/{intervention_id}/status – Lifecycle transition (human gated)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.common import PaginatedResponse
from backend.schemas.interventions import (
    InterventionCreate,
    InterventionRecord,
    InterventionStatusPatch,
)
from backend.services.intervention_service import (
    get_intervention_detail,
    get_interventions,
    propose_intervention,
    transition_intervention_status,
)

router = APIRouter(prefix="/api/v1/interventions", tags=["Retention Interventions"])


@router.get(
    "",
    response_model=PaginatedResponse[InterventionRecord],
    summary="List retention interventions",
    description=(
        "Returns paginated retention interventions with full lifecycle event history. "
        "Supports filtering by status, employee, department, and intervention type."
    ),
)
def list_interventions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    employee_id: Optional[str] = Query(None, description="Filter by employee ID"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    intervention_type: Optional[str] = Query(None, description="Filter by intervention type"),
    session: Session = Depends(get_session),
):
    return get_interventions(
        session,
        page=page,
        page_size=page_size,
        status=status,
        employee_id=employee_id,
        department_id=department_id,
        intervention_type=intervention_type,
    )


@router.post(
    "",
    response_model=InterventionRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a retention intervention",
    description=(
        "Creates a new retention intervention recommendation in CREATED state. "
        "Human review is mandatory before approval — no automated approvals permitted. "
        "Immutable audit trail is created at every lifecycle stage."
    ),
)
def create_intervention(
    body: InterventionCreate,
    actor_id: str = Query("HR_ANALYST_01", description="HR analyst creating the recommendation"),
    session: Session = Depends(get_session),
):
    try:
        return propose_intervention(session, data=body, actor_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/{intervention_id}",
    response_model=InterventionRecord,
    summary="Get intervention detail",
    description="Returns the full lifecycle record for a single retention intervention including immutable event history.",
)
def get_intervention(intervention_id: str, session: Session = Depends(get_session)):
    record = get_intervention_detail(session, intervention_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Intervention '{intervention_id}' not found.")
    return record


@router.patch(
    "/{intervention_id}/status",
    response_model=InterventionRecord,
    summary="Transition intervention lifecycle status",
    description=(
        "Advances or cancels an intervention through the human-in-the-loop lifecycle. "
        "**APPROVED transitions require a named human actor and mandatory reviewer notes.** "
        "Automated/system approvals are explicitly prohibited (Responsible AI safeguard). "
        "All transitions are permanently recorded in the immutable intervention event log."
    ),
)
def patch_intervention_status(
    intervention_id: str,
    patch: InterventionStatusPatch,
    session: Session = Depends(get_session),
):
    try:
        return transition_intervention_status(session, intervention_id=intervention_id, patch=patch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
