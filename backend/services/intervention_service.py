"""
WorkforceIQ Intervention Service Layer.
Enforces the Human-in-the-Loop Retention Intervention Lifecycle:
  CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED (and CANCELLED)

Rules:
  - No automated approvals permitted (human reviewer mandatory).
  - Every status change persists an immutable InterventionEvent audit trail.
  - State changes are recorded in audit_logs.
  - Invalid transitions raise ValueError.
"""

from datetime import date, datetime
import uuid
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.orm import (
    AuditLog,
    Department,
    Employee,
    InterventionEvent,
    RetentionIntervention,
)
from backend.schemas.common import PaginatedResponse
from backend.schemas.interventions import (
    InterventionCreate,
    InterventionEventRecord,
    InterventionRecord,
    InterventionStatusPatch,
)

# Valid state machine transitions
ALLOWED_TRANSITIONS = {
    "CREATED": {"PENDING_REVIEW", "CANCELLED"},
    "PENDING_REVIEW": {"APPROVED", "CANCELLED"},
    "APPROVED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),  # Terminal state
    "CANCELLED": set(),  # Terminal state
    # Backward compatibility with generator initial statuses
    "RECOMMENDED": {"PENDING_REVIEW", "APPROVED", "CANCELLED"},
}


def propose_intervention(
    session: Session,
    data: InterventionCreate,
    actor_id: str = "HR_ANALYST_01",
) -> InterventionRecord:
    """
    Creates a new retention intervention recommendation in CREATED or PENDING_REVIEW state.
    Requires human review before approval.
    """
    # Verify employee exists
    emp = session.execute(
        select(Employee).where(Employee.employee_id == data.employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise ValueError(f"Employee '{data.employee_id}' not found.")

    intervention_id = f"INTV-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now()

    new_intv = RetentionIntervention(
        intervention_id=intervention_id,
        employee_id=data.employee_id,
        risk_score_id=data.risk_score_id,
        intervention_type=data.intervention_type,
        status="CREATED",
        cost_usd=data.cost_usd,
        proposed_date=data.proposed_date or date.today(),
        hr_notes=data.hr_notes,
        created_at=now,
        updated_at=now,
    )
    session.add(new_intv)
    session.flush()

    # Append immutable event log
    init_event = InterventionEvent(
        intervention_id=intervention_id,
        from_status=None,
        to_status="CREATED",
        actor=actor_id,
        notes=f"Proposed intervention: {data.intervention_type}. Human review required.",
        recorded_at=now,
    )
    session.add(init_event)

    # Log in system audit logs
    audit_entry = AuditLog(
        table_name="retention_interventions",
        record_id=intervention_id,
        action="INSERT",
        old_values=None,
        new_values={
            "intervention_id": intervention_id,
            "employee_id": data.employee_id,
            "status": "CREATED",
            "type": data.intervention_type,
        },
        actor_id=actor_id,
        recorded_at=now,
    )
    session.add(audit_entry)
    session.commit()

    return get_intervention_detail(session, intervention_id)


def transition_intervention_status(
    session: Session,
    intervention_id: str,
    patch: InterventionStatusPatch,
) -> InterventionRecord:
    """
    Transitions an intervention through the human-in-the-loop lifecycle.
    Enforces strict state machine, human authorization, and audit logging.
    """
    intv = session.execute(
        select(RetentionIntervention)
        .options(selectinload(RetentionIntervention.events))
        .where(RetentionIntervention.intervention_id == intervention_id)
    ).scalar_one_or_none()

    if not intv:
        raise ValueError(f"Intervention '{intervention_id}' not found.")

    current_status = intv.status.upper()
    target_status = patch.target_status.upper()

    # 1. State machine validation
    valid_targets = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in valid_targets:
        raise ValueError(
            f"Invalid lifecycle transition: Cannot move intervention from '{current_status}' to '{target_status}'. "
            f"Allowed transitions from '{current_status}': {sorted(list(valid_targets)) or 'None (Terminal)'}."
        )

    # 2. Responsible AI Check: No automated approvals
    if target_status == "APPROVED":
        if patch.actor_id.upper() in {"SYSTEM", "AI", "AUTOMATED", "CRON"}:
            raise ValueError(
                "Responsible AI Violation: Interventions CANNOT be approved automatically by SYSTEM. "
                "A named human reviewer (e.g. HR Manager / Business Partner) is legally required."
            )
        if not patch.reviewer_notes or len(patch.reviewer_notes.strip()) < 5:
            raise ValueError(
                "Reviewer rationale notes are mandatory when approving a retention intervention."
            )

    now = datetime.now()
    old_status = current_status
    intv.status = target_status
    intv.updated_at = now

    if target_status == "IN_PROGRESS" and patch.action_date:
        intv.action_date = patch.action_date
    elif target_status == "IN_PROGRESS" and not intv.action_date:
        intv.action_date = date.today()

    if target_status == "COMPLETED":
        intv.outcome_evaluated_date = patch.outcome_evaluated_date or date.today()
        if patch.is_successful is not None:
            intv.is_successful = patch.is_successful

    if patch.reviewer_notes:
        existing_notes = intv.hr_notes or ""
        intv.hr_notes = f"{existing_notes}\n[{now.strftime('%Y-%m-%d')} by {patch.actor_id}]: {patch.reviewer_notes}".strip()

    # 3. Create immutable InterventionEvent
    event = InterventionEvent(
        intervention_id=intervention_id,
        from_status=old_status,
        to_status=target_status,
        actor=patch.actor_id,
        notes=patch.reviewer_notes,
        recorded_at=now,
    )
    session.add(event)

    # 4. System audit log
    audit_entry = AuditLog(
        table_name="retention_interventions",
        record_id=intervention_id,
        action="TRANSITION",
        old_values={"status": old_status},
        new_values={"status": target_status, "actor": patch.actor_id},
        actor_id=patch.actor_id,
        recorded_at=now,
    )
    session.add(audit_entry)
    session.commit()

    return get_intervention_detail(session, intervention_id)


def get_interventions(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    department_id: Optional[str] = None,
    intervention_type: Optional[str] = None,
) -> PaginatedResponse[InterventionRecord]:
    """
    Lists retention interventions with filtering and pagination.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 200)

    query = (
        select(
            RetentionIntervention,
            Employee.first_name,
            Employee.last_name,
            Department.department_id,
            Department.name.label("department_name"),
        )
        .join(Employee, RetentionIntervention.employee_id == Employee.employee_id)
        .join(Department, Employee.department_id == Department.department_id)
        .options(selectinload(RetentionIntervention.events))
    )

    if status:
        query = query.where(RetentionIntervention.status == status.upper())
    if employee_id:
        query = query.where(RetentionIntervention.employee_id == employee_id)
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if intervention_type:
        query = query.where(RetentionIntervention.intervention_type == intervention_type)

    # Total count
    count_subq = query.subquery()
    total_records = session.execute(select(func.count()).select_from(count_subq)).scalar() or 0

    # Order by proposed_date desc
    query = query.order_by(desc(RetentionIntervention.proposed_date), desc(RetentionIntervention.created_at))
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = session.execute(query).all()

    items = []
    for intv, first_name, last_name, dept_id, dept_name in rows:
        event_records = [
            InterventionEventRecord(
                event_id=ev.event_id,
                intervention_id=ev.intervention_id,
                from_status=ev.from_status,
                to_status=ev.to_status,
                actor=ev.actor,
                notes=ev.notes,
                recorded_at=ev.recorded_at,
            )
            for ev in intv.events
        ]
        items.append(
            InterventionRecord(
                intervention_id=intv.intervention_id,
                employee_id=intv.employee_id,
                employee_name=f"{first_name} {last_name}",
                department_id=dept_id,
                department_name=dept_name,
                risk_score_id=intv.risk_score_id,
                intervention_type=intv.intervention_type,
                status=intv.status,
                cost_usd=float(intv.cost_usd),
                proposed_date=intv.proposed_date,
                action_date=intv.action_date,
                outcome_evaluated_date=intv.outcome_evaluated_date,
                is_successful=intv.is_successful,
                hr_notes=intv.hr_notes,
                created_at=intv.created_at,
                updated_at=intv.updated_at,
                events=event_records,
            )
        )

    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return PaginatedResponse[InterventionRecord](
        total=total_records,
        page=page,
        page_size=page_size,
        pages=total_pages,
        data=items,
    )


def get_intervention_detail(session: Session, intervention_id: str) -> Optional[InterventionRecord]:
    """
    Retrieves a single intervention profile with its full immutable event audit history.
    """
    query = (
        select(
            RetentionIntervention,
            Employee.first_name,
            Employee.last_name,
            Department.department_id,
            Department.name.label("department_name"),
        )
        .join(Employee, RetentionIntervention.employee_id == Employee.employee_id)
        .join(Department, Employee.department_id == Department.department_id)
        .options(selectinload(RetentionIntervention.events))
        .where(RetentionIntervention.intervention_id == intervention_id)
    )

    row = session.execute(query).first()
    if not row:
        return None

    intv, first_name, last_name, dept_id, dept_name = row
    event_records = [
        InterventionEventRecord(
            event_id=ev.event_id,
            intervention_id=ev.intervention_id,
            from_status=ev.from_status,
            to_status=ev.to_status,
            actor=ev.actor,
            notes=ev.notes,
            recorded_at=ev.recorded_at,
        )
        for ev in sorted(intv.events, key=lambda x: x.recorded_at)
    ]

    return InterventionRecord(
        intervention_id=intv.intervention_id,
        employee_id=intv.employee_id,
        employee_name=f"{first_name} {last_name}",
        department_id=dept_id,
        department_name=dept_name,
        risk_score_id=intv.risk_score_id,
        intervention_type=intv.intervention_type,
        status=intv.status,
        cost_usd=float(intv.cost_usd),
        proposed_date=intv.proposed_date,
        action_date=intv.action_date,
        outcome_evaluated_date=intv.outcome_evaluated_date,
        is_successful=intv.is_successful,
        hr_notes=intv.hr_notes,
        created_at=intv.created_at,
        updated_at=intv.updated_at,
        events=event_records,
    )
