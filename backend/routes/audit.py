"""
WorkforceIQ – Audit Log Routes.

Endpoints:
  GET  /api/v1/audit/logs   – Paginated immutable system audit trail
  POST /api/v1/audit/logs   – Manually append an audit entry (admin use)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.audit import AuditRecord
from backend.schemas.common import PaginatedResponse
from backend.services.audit_service import get_audit_logs, log_audit

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Logs"])


@router.get(
    "/logs",
    response_model=PaginatedResponse[AuditRecord],
    summary="Paginated system audit trail",
    description=(
        "Returns the immutable system audit log with multi-criteria filtering. "
        "Every intervention lifecycle transition, data mutation, and sensitive access "
        "event is permanently recorded here."
    ),
)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    table_name: Optional[str] = Query(None, description="Filter by database table name"),
    record_id: Optional[str] = Query(None, description="Filter by specific record ID"),
    actor_id: Optional[str] = Query(None, description="Filter by actor/user ID"),
    action: Optional[str] = Query(None, description="Filter by action type (INSERT, UPDATE, TRANSITION)"),
    session: Session = Depends(get_session),
):
    return get_audit_logs(
        session,
        page=page,
        page_size=page_size,
        table_name=table_name,
        record_id=record_id,
        actor_id=actor_id,
        action=action,
    )


@router.post(
    "/logs",
    response_model=AuditRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Append audit log entry",
    description=(
        "Manually appends an immutable audit event. "
        "Intended for admin-level administrative actions not auto-captured by the system."
    ),
)
def create_audit_log(
    table_name: str = Query(description="Target table name"),
    record_id: str = Query(description="Target record primary key"),
    action: str = Query(description="Action performed (INSERT, UPDATE, DELETE, VIEW)"),
    actor_id: str = Query("ADMIN", description="Actor performing the action"),
    session: Session = Depends(get_session),
):
    return log_audit(
        session,
        table_name=table_name,
        record_id=record_id,
        action=action,
        actor_id=actor_id,
    )
