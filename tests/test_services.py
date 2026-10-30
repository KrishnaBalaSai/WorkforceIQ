"""
Automated Pytest Suite for Phase 5, Step 2: Pydantic Schemas & Service Layer.

Audits:
  1. Pydantic schema validation & serialization.
  2. Employee Service (pagination, multi-criteria filtering, sorting, 360 profiling).
  3. Department & Job Role Service (organizational aggregation, headcount, salary bands).
  4. Operational Attrition Analytics & Access-controlled Separation Trends.
  5. Longitudinal Engagement Trends & Workload Overallocation Analytics.
  6. Human-in-the-Loop Intervention Lifecycle State Machine:
     - Valid sequence: CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
     - Rejection of automated SYSTEM approvals (Responsible AI)
     - Mandatory human reviewer notes
     - Prevention of invalid state transitions
     - Immutable event tracking & audit logs
  7. Data Quality & Audit Logging services.
"""

from datetime import date, datetime
import pytest
from pydantic import ValidationError

from backend.database import _build_engine, get_session
import backend.schemas as schemas
from backend.services.analytics_service import (
    get_engagement_trends,
    get_historical_attrition_trends,
    get_operational_attrition_summary,
    get_workload_analytics,
)
from backend.services.audit_service import get_audit_logs, log_audit
from backend.services.department_service import get_departments, get_roles
from backend.services.employee_service import get_employee_detail, get_employees
from backend.services.intervention_service import (
    get_intervention_detail,
    get_interventions,
    propose_intervention,
    transition_intervention_status,
)
from backend.services.validation_service import get_anomalies, get_validation_summary


@pytest.fixture(scope="function")
def db_session():
    """Provides an isolated database session for testing."""
    engine = _build_engine()
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True, scope="module")
def cleanup_test_data():
    """Teardown fixture that purges test interventions created during test run."""
    yield
    from sqlalchemy import text
    engine = _build_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM retention_interventions WHERE intervention_id LIKE 'INTV-%'"))


# ===========================================================================
# 1. Pydantic Schema Validation Tests
# ===========================================================================

def test_schema_employee_summary_serialization():
    data = {
        "employee_id": "EMP-000001",
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@workforceiq.corp",
        "department_id": "DEP-ENG-01",
        "role_id": "ROLE-SWE-04",
        "status": "ACTIVE",
        "employment_type": "FULL_TIME",
        "work_location": "HYBRID",
        "hire_date": date(2023, 1, 15),
        "is_active": True,
        "latest_flight_risk": 0.28,
        "latest_risk_tier": "LOW",
    }
    summary = schemas.EmployeeSummary(**data)
    assert summary.employee_id == "EMP-000001"
    assert summary.latest_flight_risk == 0.28
    assert summary.latest_risk_tier == "LOW"


def test_schema_role_validation_constraints():
    # Valid role
    valid_role = schemas.RoleSummary(
        role_id="ROLE-SWE-04",
        department_id="DEP-ENG-01",
        title="Senior I Software Engineer",
        grade_level=4,
        min_salary=85000.0,
        mid_salary=105000.0,
        max_salary=125000.0,
        is_exempt=True,
    )
    assert valid_role.grade_level == 4

    # Invalid grade level (> 15) must raise ValidationError
    with pytest.raises(ValidationError):
        schemas.RoleSummary(
            role_id="ROLE-SWE-99",
            department_id="DEP-ENG-01",
            title="Invalid",
            grade_level=20,  # Invalid
            min_salary=1000.0,
            mid_salary=2000.0,
            max_salary=3000.0,
            is_exempt=True,
        )


def test_schema_intervention_create_validation():
    req = schemas.InterventionCreate(
        employee_id="EMP-000002",
        intervention_type="CAREER_DEVELOPMENT",
        cost_usd=2500.0,
        hr_notes="Scheduled quarterly executive coaching.",
    )
    assert req.cost_usd == 2500.0
    assert req.intervention_type == "CAREER_DEVELOPMENT"


# ===========================================================================
# 2. Employee Service Tests
# ===========================================================================

def test_employee_service_pagination(db_session):
    res_p1 = get_employees(db_session, page=1, page_size=20)
    assert res_p1.total == 10000
    assert len(res_p1.data) == 20
    assert res_p1.page == 1
    assert res_p1.pages == 500

    res_p2 = get_employees(db_session, page=2, page_size=20)
    assert len(res_p2.data) == 20
    assert res_p2.page == 2
    # Ensure distinct pages
    assert res_p1.data[0].employee_id != res_p2.data[0].employee_id


def test_employee_service_filtering(db_session):
    # Filter by department
    dept_res = get_employees(db_session, department_id="DEP-ENG-01", page_size=10)
    assert all(e.department_id == "DEP-ENG-01" for e in dept_res.data)

    # Filter by risk tier
    high_risk_res = get_employees(db_session, risk_tier="HIGH", page_size=10)
    assert len(high_risk_res.data) > 0
    assert all(e.latest_risk_tier == "HIGH" for e in high_risk_res.data)

    # Filter by search string
    search_res = get_employees(db_session, search="EMP-000005")
    assert search_res.total == 1
    assert search_res.data[0].employee_id == "EMP-000005"


def test_employee_service_sorting(db_session):
    res_asc = get_employees(db_session, sort_by="hire_date", sort_order="asc", page_size=5)
    dates_asc = [e.hire_date for e in res_asc.data]
    assert dates_asc == sorted(dates_asc)

    res_desc = get_employees(db_session, sort_by="hire_date", sort_order="desc", page_size=5)
    dates_desc = [e.hire_date for e in res_desc.data]
    assert dates_desc == sorted(dates_desc, reverse=True)


def test_employee_360_profile_detail(db_session):
    detail = get_employee_detail(db_session, "EMP-000002")
    assert detail is not None
    assert detail.employee_id == "EMP-000002"
    assert detail.first_name != ""
    assert detail.department is not None
    assert detail.role is not None

    # Verify longitudinal child entities populated
    assert len(detail.skills) > 0
    assert len(detail.compensation_history) > 0
    assert len(detail.performance_evaluations) > 0
    assert len(detail.engagement_surveys) > 0
    assert len(detail.project_assignments) > 0
    assert len(detail.time_off_records) > 0


def test_employee_detail_non_existent(db_session):
    assert get_employee_detail(db_session, "EMP-NONEXISTENT") is None


# ===========================================================================
# 3. Department & Job Role Service Tests
# ===========================================================================

def test_get_departments_aggregation(db_session):
    departments = get_departments(db_session)
    assert len(departments) == 8

    total_headcount = sum(d.total_headcount for d in departments)
    assert total_headcount == 10000

    for d in departments:
        assert d.active_headcount > 0
        assert d.annual_budget > 0
        assert d.average_salary is not None
        assert d.average_salary > 40000.0


def test_get_roles_service(db_session):
    roles = get_roles(db_session)
    assert len(roles) == 120

    swe_roles = get_roles(db_session, department_id="DEP-ENG-01")
    assert len(swe_roles) == 15
    for r in swe_roles:
        assert r.min_salary <= r.mid_salary <= r.max_salary


# ===========================================================================
# 4. Analytics Service Tests
# ===========================================================================

def test_operational_attrition_summary(db_session):
    summary = get_operational_attrition_summary(db_session)
    assert summary.total_active_workforce > 8500
    assert 0.0 < summary.overall_attrition_risk_avg < 1.0
    assert len(summary.retention_risk_breakdown) == 4
    assert len(summary.department_risk_breakdown) == 8
    assert len(summary.top_workforce_flight_drivers) > 0


def test_historical_attrition_access_control(db_session):
    # Unauthorized access must raise PermissionError
    with pytest.raises(PermissionError):
        get_historical_attrition_trends(db_session, is_authorized=False)

    # Authorized access succeeds
    trend = get_historical_attrition_trends(db_session, is_authorized=True)
    assert trend.total_historical_separations == 1187
    assert 5.0 <= trend.overall_voluntary_attrition_rate <= 15.0
    assert len(trend.monthly_trends) > 0


def test_engagement_trends_service(db_session):
    trend = get_engagement_trends(db_session)
    assert trend.total_surveys_analyzed > 60000
    assert 1.0 <= trend.overall_avg_satisfaction <= 5.0
    assert len(trend.trend_points) > 0


def test_workload_analytics_service(db_session):
    workload = get_workload_analytics(db_session)
    assert workload.total_active_projects == 36
    assert workload.total_assigned_employees > 8000
    assert 30.0 <= workload.average_weekly_hours <= 55.0


# ===========================================================================
# 5. Human-in-the-Loop Intervention Lifecycle Tests
# ===========================================================================

def test_intervention_lifecycle_full_flow(db_session):
    """
    Tests complete valid flow:
    CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
    """
    # 1. Propose intervention (CREATED)
    create_payload = schemas.InterventionCreate(
        employee_id="EMP-000010",
        intervention_type="COMPENSATION_INCREASE",
        cost_usd=12000.0,
        hr_notes="Identified severe compa-ratio compression (0.78). Proposing salary adjustment.",
    )
    intv = propose_intervention(db_session, create_payload, actor_id="HR_OFFICER_01")
    assert intv.status == "CREATED"
    assert len(intv.events) == 1
    assert intv.events[0].to_status == "CREATED"

    intv_id = intv.intervention_id

    # 2. Transition CREATED -> PENDING_REVIEW
    patch_review = schemas.InterventionStatusPatch(
        target_status="PENDING_REVIEW",
        actor_id="HR_OFFICER_01",
        reviewer_notes="Submitted to Compensation Committee for review.",
    )
    intv_rev = transition_intervention_status(db_session, intv_id, patch_review)
    assert intv_rev.status == "PENDING_REVIEW"
    assert len(intv_rev.events) == 2

    # 3. Transition PENDING_REVIEW -> APPROVED (Human reviewer mandatory)
    patch_approve = schemas.InterventionStatusPatch(
        target_status="APPROVED",
        actor_id="VP_HR_JANE_DOE",
        reviewer_notes="Approved 12k market adjustment based on high flight risk.",
    )
    intv_app = transition_intervention_status(db_session, intv_id, patch_approve)
    assert intv_app.status == "APPROVED"
    assert len(intv_app.events) == 3

    # 4. Transition APPROVED -> IN_PROGRESS
    patch_progress = schemas.InterventionStatusPatch(
        target_status="IN_PROGRESS",
        actor_id="HR_OFFICER_01",
        reviewer_notes="Communicated offer to employee in supportive retention conversation.",
        action_date=date.today(),
    )
    intv_prog = transition_intervention_status(db_session, intv_id, patch_progress)
    assert intv_prog.status == "IN_PROGRESS"
    assert intv_prog.action_date is not None
    assert len(intv_prog.events) == 4

    # 5. Transition IN_PROGRESS -> COMPLETED
    patch_complete = schemas.InterventionStatusPatch(
        target_status="COMPLETED",
        actor_id="HR_OFFICER_01",
        reviewer_notes="Employee accepted compensation revision. Retention secured.",
        outcome_evaluated_date=date.today(),
        is_successful=True,
    )
    intv_done = transition_intervention_status(db_session, intv_id, patch_complete)
    assert intv_done.status == "COMPLETED"
    assert intv_done.is_successful is True
    assert len(intv_done.events) == 5

    # Verify audit logs captured all events
    audit_logs = get_audit_logs(db_session, table_name="retention_interventions", record_id=intv_id)
    assert audit_logs.total >= 5


def test_intervention_rejects_automated_approval(db_session):
    """
    Responsible AI Safeguard: Interventions CANNOT be approved automatically by SYSTEM.
    """
    create_payload = schemas.InterventionCreate(
        employee_id="EMP-000015",
        intervention_type="RETENTION_BONUS",
        cost_usd=5000.0,
        hr_notes="Retention bonus candidate.",
    )
    intv = propose_intervention(db_session, create_payload, actor_id="HR_OFFICER_01")
    intv_id = intv.intervention_id

    # Move to PENDING_REVIEW
    transition_intervention_status(
        db_session,
        intv_id,
        schemas.InterventionStatusPatch(
            target_status="PENDING_REVIEW",
            actor_id="HR_OFFICER_01",
            reviewer_notes="Ready for review.",
        ),
    )

    # Attempt automated approval via SYSTEM must FAIL
    with pytest.raises(ValueError, match="Responsible AI Violation"):
        transition_intervention_status(
            db_session,
            intv_id,
            schemas.InterventionStatusPatch(
                target_status="APPROVED",
                actor_id="SYSTEM",  # Disallowed
                reviewer_notes="Automated rule matched.",
            ),
        )


def test_intervention_requires_reviewer_rationale(db_session):
    """Approval requires meaningful human notes."""
    create_payload = schemas.InterventionCreate(
        employee_id="EMP-000020",
        intervention_type="ROLE_PROMOTION",
        cost_usd=0.0,
        hr_notes="Promotion review.",
    )
    intv = propose_intervention(db_session, create_payload, actor_id="HR_OFFICER_01")
    intv_id = intv.intervention_id

    transition_intervention_status(
        db_session,
        intv_id,
        schemas.InterventionStatusPatch(
            target_status="PENDING_REVIEW",
            actor_id="HR_OFFICER_01",
            reviewer_notes="Ready for review.",
        ),
    )

    # Approval without notes must fail
    with pytest.raises(ValueError, match="Reviewer rationale notes are mandatory"):
        transition_intervention_status(
            db_session,
            intv_id,
            schemas.InterventionStatusPatch(
                target_status="APPROVED",
                actor_id="HR_DIR_ROBERT",
                reviewer_notes="",  # Empty notes
            ),
        )


def test_intervention_invalid_transition_rejected(db_session):
    """Illegal state jumps (e.g. CREATED -> APPROVED or COMPLETED -> PENDING_REVIEW) must fail."""
    create_payload = schemas.InterventionCreate(
        employee_id="EMP-000025",
        intervention_type="FLEXIBLE_WORK_SCHEDULE",
        cost_usd=0.0,
        hr_notes="Flexible hours proposal.",
    )
    intv = propose_intervention(db_session, create_payload, actor_id="HR_OFFICER_01")
    intv_id = intv.intervention_id

    # Attempt to jump straight from CREATED to APPROVED (bypassing review)
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        transition_intervention_status(
            db_session,
            intv_id,
            schemas.InterventionStatusPatch(
                target_status="APPROVED",
                actor_id="HR_DIR_ROBERT",
                reviewer_notes="Attempted jump.",
            ),
        )


# ===========================================================================
# 6. Validation and Audit Service Tests
# ===========================================================================

def test_validation_summary_service():
    summary = get_validation_summary()
    assert summary.status == "PASSED"
    assert summary.total_pillars_evaluated == 12
    assert summary.passed_pillars_count == 12
    assert summary.total_violations_count == 0


def test_anomalies_query_service(db_session):
    anoms = get_anomalies(db_session, page_size=20)
    assert anoms.total == 148
    assert len(anoms.data) == 20

    # Filter by severity
    critical_anoms = get_anomalies(db_session, severity="CRITICAL")
    assert critical_anoms.total > 0
    assert all(a["severity"] == "CRITICAL" for a in critical_anoms.data)


def test_audit_log_service(db_session):
    entry = log_audit(
        db_session,
        table_name="employees",
        record_id="EMP-000001",
        action="ACCESS",
        old_values=None,
        new_values={"viewed_by": "HR_ADMIN"},
        actor_id="HR_ADMIN",
        client_ip="127.0.0.1",
    )
    assert entry.log_id > 0
    assert entry.action == "ACCESS"

    logs = get_audit_logs(db_session, table_name="employees", record_id="EMP-000001")
    assert logs.total > 0
    assert any(l.log_id == entry.log_id for l in logs.data)
