"""
WorkforceIQ Audit Logging Service Layer.
Tracks system modifications and sensitive state transitions.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.models.orm import AuditLog
from backend.schemas.audit import AuditRecord
from backend.schemas.common import PaginatedResponse


def log_audit(
    session: Session,
    table_name: str,
    record_id: str,
    action: str,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    actor_id: str = "SYSTEM",
    client_ip: Optional[str] = None,
) -> AuditRecord:
    """
    Appends an immutable audit log record.
    """
    entry = AuditLog(
        table_name=table_name,
        record_id=str(record_id),
        action=action.upper(),
        old_values=old_values,
        new_values=new_values,
        actor_id=actor_id,
        client_ip=client_ip,
        recorded_at=datetime.now(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    return AuditRecord(
        log_id=entry.log_id,
        table_name=entry.table_name,
        record_id=entry.record_id,
        action=entry.action,
        old_values=entry.old_values,
        new_values=entry.new_values,
        actor_id=entry.actor_id,
        client_ip=entry.client_ip,
        recorded_at=entry.recorded_at,
    )


def get_audit_logs(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
) -> PaginatedResponse[AuditRecord]:
    """
    Retrieves paginated audit log history with multi-criteria filtering.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 200)

    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    if record_id:
        query = query.where(AuditLog.record_id == str(record_id))
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if action:
        query = query.where(AuditLog.action == action.upper())

    total_records = session.execute(
        select(func.count()).select_from(query.subquery())
    ).scalar() or 0

    query = query.order_by(desc(AuditLog.recorded_at))
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = session.execute(query).scalars().all()

    items = [
        AuditRecord(
            log_id=r.log_id,
            table_name=r.table_name,
            record_id=r.record_id,
            action=r.action,
            old_values=r.old_values,
            new_values=r.new_values,
            actor_id=r.actor_id,
            client_ip=r.client_ip,
            recorded_at=r.recorded_at,
        )
        for r in rows
    ]

    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return PaginatedResponse[AuditRecord](
        total=total_records,
        page=page,
        page_size=page_size,
        pages=total_pages,
        data=items,
    )
