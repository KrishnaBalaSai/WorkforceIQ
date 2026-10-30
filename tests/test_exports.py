"""
WorkforceIQ – Automated Pytest Suite for Phase 8: Data Exports and Reporting.

Covers:
  1. Export manifest & catalog inspection.
  2. CSV downloads with proper media type and SHA-256 header.
  3. JSON downloads with ExportEnvelope, manifest metadata, and integrity checksum.
  4. Query filtering and parameter reflection (department, status, date ranges).
  5. Empty dataset / edge-case filter handling.
  6. Ground-truth isolation:
     - Rejection of unauthenticated / un-authorized access to historical separations (403).
     - Success with a valid X-HR-Analytics-Token header.
     - Verification that operational exports NEVER expose ground-truth exit reasons or training labels.
  7. Downloadable executive report structure and metrics.
"""
import os
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app

HR_ANALYTICS_TOKEN = os.environ.get("HR_ANALYTICS_TOKEN", "")
assert HR_ANALYTICS_TOKEN, "HR_ANALYTICS_TOKEN must be configured in .env"

HR_AUTH_HEADERS = {"X-HR-Analytics-Token": HR_ANALYTICS_TOKEN}

@pytest.fixture(scope="module")
def client():
    """Provides reusable FastAPI TestClient."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Export Catalog & Manifest
# ---------------------------------------------------------------------------
def test_export_manifest_catalog(client: TestClient):
    response = client.get("/api/v1/exports/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "WorkforceIQ Export & Reporting Service"
    assert "supported_formats" in data
    assert "datasets" in data
    dataset_ids = [d["id"] for d in data["datasets"]]
    assert "employees" in dataset_ids
    assert "departments" in dataset_ids
    assert "retention-risk" in dataset_ids
    assert "interventions" in dataset_ids
    assert "engagement" in dataset_ids
    assert "workload" in dataset_ids
    assert "validation" in dataset_ids
    assert "model-metrics" in dataset_ids
    assert "historical-separations" in dataset_ids


# ---------------------------------------------------------------------------
# 2. Employee Directory Exports (CSV & JSON)
# ---------------------------------------------------------------------------
def test_export_employees_csv_and_checksum(client: TestClient):
    response = client.get("/api/v1/exports/employees.csv?limit=50")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=\"workforceiq_employees.csv\"" in response.headers["content-disposition"]
    assert "x-checksum-sha256" in response.headers

    # Validate checksum calculation
    expected_hash = hashlib.sha256(response.content).hexdigest()
    assert response.headers["x-checksum-sha256"] == expected_hash

    # Verify CSV structure
    lines = response.text.strip().split("\r\n") if "\r\n" in response.text else response.text.strip().split("\n")
    header = lines[0].split(",")
    assert "employee_id" in header
    assert "email" in header
    assert "department" in header
    # Ensure NO ground-truth exit reasons or training labels leaked in operational employee export
    assert "separation_type" not in header
    assert "voluntary_exit" not in header
    assert len(lines) > 1


def test_export_employees_json_with_envelope(client: TestClient):
    response = client.get("/api/v1/exports/employees.json?limit=25")
    assert response.status_code == 200
    envelope = response.json()
    assert "manifest" in envelope
    assert "data" in envelope
    manifest = envelope["manifest"]
    assert manifest["dataset_name"] == "employees"
    assert manifest["export_format"] == "json"
    assert manifest["record_count"] == len(envelope["data"])
    assert "sha256_checksum" in manifest
    assert "responsible_ai_notice" in manifest


def test_export_employees_filtering(client: TestClient):
    # Filter by work location
    res_remote = client.get("/api/v1/exports/employees.json?work_location=REMOTE&limit=100")
    assert res_remote.status_code == 200
    data = res_remote.json()["data"]
    for emp in data:
        assert emp["work_location"] == "REMOTE"

    # Filter with non-existent department returns empty data without crashing
    res_empty = client.get("/api/v1/exports/employees.json?department_id=NON_EXISTENT_DEPT")
    assert res_empty.status_code == 200
    envelope = res_empty.json()
    assert envelope["data"] == []
    assert envelope["manifest"]["record_count"] == 0


# ---------------------------------------------------------------------------
# 3. Department Analytics Exports
# ---------------------------------------------------------------------------
def test_export_departments_csv_and_json(client: TestClient):
    r_csv = client.get("/api/v1/exports/departments.csv")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "department_id,department_name" in r_csv.text

    r_json = client.get("/api/v1/exports/departments.json")
    assert r_json.status_code == 200
    envelope = r_json.json()
    assert envelope["manifest"]["record_count"] == 8
    assert len(envelope["data"]) == 8


# ---------------------------------------------------------------------------
# 4. Retention Risk Exports & Responsible AI Disclaimers
# ---------------------------------------------------------------------------
def test_export_retention_risk_dataset(client: TestClient):
    r_csv = client.get("/api/v1/exports/retention-risk.csv")
    assert r_csv.status_code == 200
    assert "flight_risk_probability" in r_csv.text
    assert "primary_risk_driver" in r_csv.text

    # JSON with tier filter
    r_json = client.get("/api/v1/exports/retention-risk.json?risk_tier=HIGH")
    assert r_json.status_code == 200
    data = r_json.json()["data"]
    for item in data:
        assert item["risk_tier"] == "HIGH"
        # Disclaimers present
        assert "Statistical association" in item["disclaimer"]


# ---------------------------------------------------------------------------
# 5. Interventions Exports
# ---------------------------------------------------------------------------
def test_export_interventions_dataset(client: TestClient):
    r_csv = client.get("/api/v1/exports/interventions.csv")
    assert r_csv.status_code == 200
    assert "intervention_id,employee_id" in r_csv.text

    r_json = client.get("/api/v1/exports/interventions.json")
    assert r_json.status_code == 200
    assert "data" in r_json.json()


# ---------------------------------------------------------------------------
# 6. Engagement & Workload Exports
# ---------------------------------------------------------------------------
def test_export_engagement_and_workload(client: TestClient):
    # Engagement
    r_eng = client.get("/api/v1/exports/engagement.json?limit=20")
    assert r_eng.status_code == 200
    assert len(r_eng.json()["data"]) <= 20

    # Workload with overtime flag filter
    r_wl = client.get("/api/v1/exports/workload.json?is_overallocated=true&limit=20")
    assert r_wl.status_code == 200
    for w in r_wl.json()["data"]:
        assert w["is_overtime_risk"] is True
        assert w["weekly_logged_hours"] > 45.0


# ---------------------------------------------------------------------------
# 7. Validation & Model Metrics Exports
# ---------------------------------------------------------------------------
def test_export_validation_and_model_metrics(client: TestClient):
    # Validation 12-pillar audit
    r_val = client.get("/api/v1/exports/validation.json")
    assert r_val.status_code == 200
    data = r_val.json()["data"]
    assert len(data) == 12
    for p in data:
        assert p["status"] == "PASSED"

    # Model metrics
    r_mm = client.get("/api/v1/exports/model-metrics.json")
    assert r_mm.status_code == 200
    record = r_mm.json()["data"][0]
    assert record["algorithm"] == "RandomForest"
    assert record["test_roc_auc"] > 0.85
    assert record["prediction_horizon_days"] == 90


# ---------------------------------------------------------------------------
# 8. Ground-Truth Isolation & Authorization Enforcement
# ---------------------------------------------------------------------------
def test_historical_separations_requires_hr_authorization(client: TestClient):
    # Missing header -> 403
    r_missing = client.get("/api/v1/exports/historical-separations.csv")
    assert r_missing.status_code == 403

    # Invalid token -> 403
    r_invalid = client.get(
        "/api/v1/exports/historical-separations.json",
        headers={"X-HR-Analytics-Token": "invalid-token"},
    )
    assert r_invalid.status_code == 403

    # Valid token -> 200
    r_auth = client.get(
        "/api/v1/exports/historical-separations.json",
        headers=HR_AUTH_HEADERS,
    )
    assert r_auth.status_code == 200

    envelope = r_auth.json()
    assert envelope["manifest"]["data_classification"] == "RESTRICTED_GROUND_TRUTH"
    assert envelope["manifest"]["record_count"] == 1187
    assert len(envelope["data"]) == 1187


# ---------------------------------------------------------------------------
# 9. Executive Intelligence Report
# ---------------------------------------------------------------------------
def test_downloadable_executive_report(client: TestClient):
    response = client.get("/api/v1/exports/reports/executive")
    assert response.status_code == 200
    report = response.json()
    assert report["report_title"] == "WorkforceIQ Executive Retention Intelligence Report"
    assert report["active_headcount"] == 8813
    assert report["validation_status"] == "PASSED (12 of 12 pillars)"
    assert len(report["departments_summary"]) == 8
    assert "Responsible AI" in report["governance_notes"]
