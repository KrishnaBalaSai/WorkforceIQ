"""
WorkforceIQ – Automated Pytest Suite for Phase 5, Step 3: FastAPI REST Endpoints.

Comprehensive test suite covering:
  1. Service health checks (/health, /health/ready, /)
  2. Employee 360 & Directory (pagination, multi-criteria filtering, sorting, 404s)
  3. Department & Job Role APIs (aggregations, headcount, role bands)
  4. Operational Attrition Intelligence & Access-Controlled Historical Separation Trends
  5. Longitudinal Engagement Trends & Workload Overallocation APIs
  6. Human-in-the-Loop Retention Intervention Lifecycle & Governance:
     - Proposal creation (POST)
     - Detail retrieval (GET)
     - Responsible AI guardrail: Automated SYSTEM approval rejection (422)
     - Mandatory reviewer rationale requirement (422)
     - State machine transition rules (422 on invalid jump)
     - Complete human lifecycle: CREATED -> PENDING_REVIEW -> APPROVED -> IN_PROGRESS -> COMPLETED
  7. Data Quality & 12-Pillar Validation APIs
  8. Immutable Audit Trail APIs
  9. Ground-Truth Data Isolation Enforcement
"""

from datetime import date
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a reusable FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Health & Root Endpoints
# ---------------------------------------------------------------------------

def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "WorkforceIQ" in data["service"]
    assert data["version"] == "1.0.0"
    assert "docs_url" in data
    assert "health_check" in data


def test_health_liveness(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"healthy", "degraded"}
    assert data["database_type"] == "postgresql"
    assert data["postgresql_reachable"] is True
    assert "timestamp" in data


def test_health_readiness(client: TestClient):
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "postgresql"


# ---------------------------------------------------------------------------
# 2. Employee Endpoints
# ---------------------------------------------------------------------------

def test_employees_list_pagination(client: TestClient):
    response = client.get("/api/v1/employees?page=1&page_size=25")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10000
    assert data["page"] == 1
    assert data["page_size"] == 25
    assert len(data["data"]) == 25

    first_emp = data["data"][0]
    assert "employee_id" in first_emp
    assert "email" in first_emp
    assert "department_id" in first_emp
    assert "status" in first_emp


def test_employees_filtering_by_department(client: TestClient):
    response = client.get("/api/v1/employees?department_id=DEP-ENG-01&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for emp in data["data"]:
        assert emp["department_id"] == "DEP-ENG-01"


def test_employees_filtering_by_status(client: TestClient):
    response = client.get("/api/v1/employees?status=ACTIVE&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for emp in data["data"]:
        assert emp["status"] == "ACTIVE"


def test_employees_filtering_by_risk_tier(client: TestClient):
    response = client.get("/api/v1/employees?risk_tier=HIGH&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for emp in data["data"]:
        assert emp["latest_risk_tier"] == "HIGH"


def test_employees_search(client: TestClient):
    response = client.get("/api/v1/employees?search=EMP-000001")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    emp_ids = [e["employee_id"] for e in data["data"]]
    assert "EMP-000001" in emp_ids


def test_employees_sorting(client: TestClient):
    response = client.get("/api/v1/employees?sort_by=first_name&sort_order=asc&page_size=10")
    assert response.status_code == 200
    names = [e["first_name"] for e in response.json()["data"]]
    assert names == sorted(names)


def test_employee_360_profile(client: TestClient):
    response = client.get("/api/v1/employees/EMP-000001")
    assert response.status_code == 200
    emp = response.json()
    assert emp["employee_id"] == "EMP-000001"
    assert "department" in emp
    assert "role" in emp
    assert "skills" in emp
    assert "compensation_history" in emp
    assert "performance_evaluations" in emp
    assert "engagement_surveys" in emp
    assert "project_assignments" in emp
    assert "time_off_records" in emp
    assert "latest_flight_risk" in emp


def test_employee_detail_not_found(client: TestClient):
    response = client.get("/api/v1/employees/EMP-9999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Department & Job Role Endpoints
# ---------------------------------------------------------------------------

def test_departments_list(client: TestClient):
    response = client.get("/api/v1/departments")
    assert response.status_code == 200
    depts = response.json()
    assert len(depts) == 8
    dept_ids = {d["department_id"] for d in depts}
    assert "DEP-ENG-01" in dept_ids
    for d in depts:
        assert d["total_headcount"] > 0
        assert d["active_headcount"] > 0
        assert d["average_salary"] > 0


def test_department_detail(client: TestClient):
    response = client.get("/api/v1/departments/DEP-ENG-01")
    assert response.status_code == 200
    dept = response.json()
    assert dept["department_id"] == "DEP-ENG-01"
    assert dept["name"] == "Software Engineering"


def test_department_detail_not_found(client: TestClient):
    response = client.get("/api/v1/departments/DEP-NONEXISTENT")
    assert response.status_code == 404


def test_roles_list(client: TestClient):
    response = client.get("/api/v1/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) == 120
    for r in roles:
        assert 1 <= r["grade_level"] <= 15
        assert r["min_salary"] <= r["mid_salary"] <= r["max_salary"]


def test_roles_filtered_by_department(client: TestClient):
    response = client.get("/api/v1/roles?department_id=DEP-ENG-01")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) > 0
    for r in roles:
        assert r["department_id"] == "DEP-ENG-01"


# ---------------------------------------------------------------------------
# 4. Attrition Intelligence & Access-Controlled Trends
# ---------------------------------------------------------------------------

def test_attrition_summary_operational(client: TestClient):
    response = client.get("/api/v1/attrition/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_active_workforce"] > 0
    assert 0.0 <= summary["overall_attrition_risk_avg"] <= 1.0
    assert len(summary["retention_risk_breakdown"]) > 0
    assert len(summary["department_risk_breakdown"]) == 8


def test_attrition_trends_restricted_without_header(client: TestClient):
    """Responsible AI: Historical separation outcomes require HR authorization."""
    response = client.get("/api/v1/attrition/trends")
    assert response.status_code == 403
    assert "authorization" in response.json()["detail"].lower()


def test_attrition_trends_restricted_with_false_header(client: TestClient):
    response = client.get("/api/v1/attrition/trends", headers={"X-HR-Authorization": "false"})
    assert response.status_code == 403


def test_attrition_trends_authorized(client: TestClient):
    response = client.get("/api/v1/attrition/trends", headers={"X-HR-Authorization": "true"})
    assert response.status_code == 200
    trends = response.json()
    assert trends["analysis_window_months"] == 24
    assert trends["total_historical_separations"] > 0
    assert len(trends["monthly_trends"]) == 24


# ---------------------------------------------------------------------------
# 5. Engagement & Workload Analytics
# ---------------------------------------------------------------------------

def test_engagement_trends_endpoint(client: TestClient):
    response = client.get("/api/v1/engagement/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_surveys_analyzed"] > 0
    assert len(data["trend_points"]) > 0


def test_engagement_trends_with_department(client: TestClient):
    response = client.get("/api/v1/engagement/trends?department_id=DEP-ENG-01")
    assert response.status_code == 200
    data = response.json()
    assert data["department_id"] == "DEP-ENG-01"


def test_workload_analytics_endpoint(client: TestClient):
    response = client.get("/api/v1/workload/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_active_projects"] > 0
    assert data["total_assigned_employees"] > 0
    assert data["average_weekly_hours"] > 0


# ---------------------------------------------------------------------------
# 6. Human-in-the-Loop Retention Interventions & Governance
# ---------------------------------------------------------------------------

def test_intervention_crud_and_lifecycle(client: TestClient):
    # Step 1: Propose intervention (CREATED)
    create_payload = {
        "employee_id": "EMP-000001",
        "intervention_type": "Executive Career Mentoring",
        "cost_usd": 1500.0,
        "hr_notes": "Identified high flight risk. Supportive conversation recommended.",
    }
    create_res = client.post("/api/v1/interventions?actor_id=HR_SPECIALIST_01", json=create_payload)
    assert create_res.status_code == 201
    intv = create_res.json()
    intv_id = intv["intervention_id"]
    assert intv["status"] == "CREATED"
    assert intv["employee_id"] == "EMP-000001"

    # Step 2: Retrieve detail
    detail_res = client.get(f"/api/v1/interventions/{intv_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["intervention_id"] == intv_id
    assert len(detail_res.json()["events"]) >= 1

    # Step 3: Advance to PENDING_REVIEW
    patch_review = {
        "target_status": "PENDING_REVIEW",
        "actor_id": "HR_SPECIALIST_01",
        "reviewer_notes": "Submitted for leadership review.",
    }
    review_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=patch_review)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "PENDING_REVIEW"

    # Step 4: Responsible AI Guardrail – Automated SYSTEM approval MUST be rejected
    auto_approve = {
        "target_status": "APPROVED",
        "actor_id": "SYSTEM",
        "reviewer_notes": "Automated pipeline approval.",
    }
    auto_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=auto_approve)
    assert auto_res.status_code == 422
    assert "responsible ai violation" in auto_res.json()["detail"].lower()

    # Step 5: Responsible AI Guardrail – Approval without notes MUST be rejected
    no_notes_approve = {
        "target_status": "APPROVED",
        "actor_id": "HR_DIRECTOR_JANE",
        "reviewer_notes": "",
    }
    no_notes_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=no_notes_approve)
    assert no_notes_res.status_code == 422
    assert "mandatory" in no_notes_res.json()["detail"].lower()

    # Step 6: Valid Human Approval
    human_approve = {
        "target_status": "APPROVED",
        "actor_id": "HR_DIRECTOR_JANE",
        "reviewer_notes": "Approved after reviewing employee career trajectory and retention impact.",
    }
    approve_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=human_approve)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # Step 7: Transition to IN_PROGRESS
    progress_patch = {
        "target_status": "IN_PROGRESS",
        "actor_id": "HR_BUSINESS_PARTNER",
        "reviewer_notes": "Mentoring sessions scheduled with VP of Engineering.",
    }
    progress_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=progress_patch)
    assert progress_res.status_code == 200
    assert progress_res.json()["status"] == "IN_PROGRESS"

    # Step 8: Complete Intervention
    complete_patch = {
        "target_status": "COMPLETED",
        "actor_id": "HR_BUSINESS_PARTNER",
        "reviewer_notes": "All sessions completed; employee engagement renewed.",
        "is_successful": True,
    }
    complete_res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=complete_patch)
    assert complete_res.status_code == 200
    final_intv = complete_res.json()
    assert final_intv["status"] == "COMPLETED"
    assert final_intv["is_successful"] is True
    assert len(final_intv["events"]) == 5  # CREATED, PENDING_REVIEW, APPROVED, IN_PROGRESS, COMPLETED


def test_intervention_invalid_state_transition(client: TestClient):
    create_payload = {
        "employee_id": "EMP-000002",
        "intervention_type": "Flexible Work Schedule",
    }
    create_res = client.post("/api/v1/interventions", json=create_payload)
    assert create_res.status_code == 201
    intv_id = create_res.json()["intervention_id"]

    # Attempting to jump directly from CREATED to COMPLETED must fail
    invalid_patch = {
        "target_status": "COMPLETED",
        "actor_id": "HR_ANALYST",
        "reviewer_notes": "Trying to skip review.",
    }
    res = client.patch(f"/api/v1/interventions/{intv_id}/status", json=invalid_patch)
    assert res.status_code == 422
    assert "invalid lifecycle transition" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 7. Data Validation & Anomaly Endpoints
# ---------------------------------------------------------------------------

def test_validation_summary_endpoint(client: TestClient):
    response = client.get("/api/v1/validation/summary")
    assert response.status_code == 200
    val = response.json()
    assert val["status"] == "PASSED"
    assert val["total_pillars_evaluated"] == 12
    assert val["passed_pillars_count"] == 12
    assert val["failed_pillars_count"] == 0
    assert val["total_violations_count"] == 0


def test_anomalies_list_endpoint(client: TestClient):
    response = client.get("/api/v1/validation/anomalies?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 148
    assert len(data["data"]) == 20


# ---------------------------------------------------------------------------
# 8. Audit Logging Endpoints
# ---------------------------------------------------------------------------

def test_audit_logs_endpoints(client: TestClient):
    # Query existing audit logs
    get_res = client.get("/api/v1/audit/logs?page=1&page_size=10")
    assert get_res.status_code == 200
    logs = get_res.json()
    assert logs["total"] > 0
    assert len(logs["data"]) > 0

    # Manually append an audit entry
    post_res = client.post(
        "/api/v1/audit/logs?table_name=system_settings&record_id=CFG-001&action=UPDATE&actor_id=SUPER_ADMIN"
    )
    assert post_res.status_code == 201
    created_log = post_res.json()
    assert created_log["table_name"] == "system_settings"
    assert created_log["action"] == "UPDATE"
    assert created_log["actor_id"] == "SUPER_ADMIN"


# ---------------------------------------------------------------------------
# 9. Ground-Truth Data Isolation Enforcement
# ---------------------------------------------------------------------------

def test_ground_truth_isolation_in_employee_profile(client: TestClient):
    """
    Ensures Employee 360 profile does NOT include exit_records or ground-truth evaluation labels.
    """
    response = client.get("/api/v1/employees/EMP-000001")
    assert response.status_code == 200
    emp_data = response.json()

    # Neither exit_records nor ground-truth attrition labels should appear in operational detail
    assert "exit_records" not in emp_data
    assert "attrition_label" not in emp_data
    assert "actual_attrition" not in emp_data
