"""
WorkforceIQ – Data Export and Reporting Routes (Phase 8).

Endpoints:
  GET /api/v1/exports/manifest               – Lists available exportable datasets and metadata
  GET /api/v1/exports/employees.csv          – CSV export of employee directory
  GET /api/v1/exports/employees.json         – JSON export with manifest and checksum
  GET /api/v1/exports/departments.csv        – CSV export of department statistics
  GET /api/v1/exports/departments.json       – JSON export of department statistics
  GET /api/v1/exports/retention-risk.csv     – CSV export of prospective risk scores
  GET /api/v1/exports/retention-risk.json    – JSON export of prospective risk scores
  GET /api/v1/exports/interventions.csv      – CSV export of retention interventions
  GET /api/v1/exports/interventions.json     – JSON export of retention interventions
  GET /api/v1/exports/engagement.csv         – CSV export of engagement surveys
  GET /api/v1/exports/engagement.json        – JSON export of engagement surveys
  GET /api/v1/exports/workload.csv           – CSV export of workload and project hours
  GET /api/v1/exports/workload.json          – JSON export of workload and project hours
  GET /api/v1/exports/validation.csv         – CSV export of 12-pillar validation
  GET /api/v1/exports/validation.json        – JSON export of 12-pillar validation
  GET /api/v1/exports/model-metrics.csv      – CSV export of ML model benchmarking & calibration
  GET /api/v1/exports/model-metrics.json     – JSON export of ML model benchmarking & calibration
  GET /api/v1/exports/historical-separations.csv  – RESTRICTED HR ground-truth CSV export
  GET /api/v1/exports/historical-separations.json – RESTRICTED HR ground-truth JSON export
  GET /api/v1/exports/reports/executive      – Structured Executive Intelligence Report
"""

from datetime import date
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.exports import ExportEnvelope, ExportManifest
from backend.services.export_service import ExportService, compute_sha256

router = APIRouter(prefix="/api/v1/exports", tags=["Data Exports & Reporting"])


def _csv_response(csv_content: str, filename: str) -> Response:
    """Helper to return CSV file download with proper headers and checksum."""
    payload_bytes = csv_content.encode("utf-8")
    checksum = compute_sha256(payload_bytes)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
        "X-Checksum-SHA256": checksum,
    }
    return Response(content=payload_bytes, media_type="text/csv", headers=headers)


# ---------------------------------------------------------------------------
# 0. Export Manifest Catalog
# ---------------------------------------------------------------------------
@router.get(
    "/manifest",
    summary="List available exportable datasets and metadata",
    description="Returns catalogue of exportable operational and restricted datasets.",
)
def get_export_catalog():
    return {
        "service": "WorkforceIQ Export & Reporting Service",
        "version": "1.0.0",
        "supported_formats": ["csv", "json"],
        "datasets": [
            {
                "id": "employees",
                "name": "Employee Directory",
                "classification": "OPERATIONAL_INTERNAL",
                "description": "Active and historical workforce records excluding ground-truth exit reasons.",
                "endpoints": ["/api/v1/exports/employees.csv", "/api/v1/exports/employees.json"],
            },
            {
                "id": "departments",
                "name": "Department Analytics",
                "classification": "OPERATIONAL_INTERNAL",
                "description": "Headcount, cost center, and organizational aggregation metrics.",
                "endpoints": ["/api/v1/exports/departments.csv", "/api/v1/exports/departments.json"],
            },
            {
                "id": "retention-risk",
                "name": "Retention Risk Scores",
                "classification": "OPERATIONAL_CONFIDENTIAL",
                "description": "Prospective Platt-calibrated flight risk probabilities and top SHAP drivers.",
                "endpoints": ["/api/v1/exports/retention-risk.csv", "/api/v1/exports/retention-risk.json"],
            },
            {
                "id": "interventions",
                "name": "Retention Interventions",
                "classification": "OPERATIONAL_CONFIDENTIAL",
                "description": "Human-in-the-loop retention action proposals, statuses, and audit records.",
                "endpoints": ["/api/v1/exports/interventions.csv", "/api/v1/exports/interventions.json"],
            },
            {
                "id": "engagement",
                "name": "Engagement Surveys",
                "classification": "OPERATIONAL_CONFIDENTIAL",
                "description": "Longitudinal survey metrics: satisfaction, trust, work-life balance, sentiment.",
                "endpoints": ["/api/v1/exports/engagement.csv", "/api/v1/exports/engagement.json"],
            },
            {
                "id": "workload",
                "name": "Workload & Project Assignments",
                "classification": "OPERATIONAL_INTERNAL",
                "description": "Project allocations, weekly hours, and overtime fatigue flags (>45h).",
                "endpoints": ["/api/v1/exports/workload.csv", "/api/v1/exports/workload.json"],
            },
            {
                "id": "validation",
                "name": "Data Quality 12-Pillar Validation",
                "classification": "PUBLIC_TECHNICAL",
                "description": "Audit scorecard and referential integrity check results.",
                "endpoints": ["/api/v1/exports/validation.csv", "/api/v1/exports/validation.json"],
            },
            {
                "id": "model-metrics",
                "name": "ML Model Performance & Calibration",
                "classification": "PUBLIC_TECHNICAL",
                "description": "Model benchmark metrics: PR-AUC, ROC-AUC, Brier score, ECE, threshold sweep.",
                "endpoints": ["/api/v1/exports/model-metrics.csv", "/api/v1/exports/model-metrics.json"],
            },
            {
                "id": "historical-separations",
                "name": "Historical Separation Records",
                "classification": "RESTRICTED_GROUND_TRUTH",
                "description": "Requires HR Analytics authorization header (X-HR-Authorization: true).",
                "endpoints": ["/api/v1/exports/historical-separations.csv", "/api/v1/exports/historical-separations.json"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# 1. Employees Exports
# ---------------------------------------------------------------------------
@router.get("/employees.csv", summary="Export Employee Directory as CSV")
def export_employees_csv(
    department_id: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    work_location: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_employees_dataset(
        department_id=department_id,
        role_id=role_id,
        status=status,
        work_location=work_location,
        limit=limit,
    )
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_employees.csv")


@router.get("/employees.json", response_model=ExportEnvelope, summary="Export Employee Directory as JSON")
def export_employees_json(
    department_id: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    work_location: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_employees_dataset(
        department_id=department_id,
        role_id=role_id,
        status=status,
        work_location=work_location,
        limit=limit,
    )
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    params = {"department_id": department_id, "role_id": role_id, "status": status, "work_location": work_location, "limit": limit}
    return service.build_export_envelope("employees", "json", data, payload_bytes, params)


# ---------------------------------------------------------------------------
# 2. Department Exports
# ---------------------------------------------------------------------------
@router.get("/departments.csv", summary="Export Department Analytics as CSV")
def export_departments_csv(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_departments_dataset()
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_departments.csv")


@router.get("/departments.json", response_model=ExportEnvelope, summary="Export Department Analytics as JSON")
def export_departments_json(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_departments_dataset()
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    return service.build_export_envelope("departments", "json", data, payload_bytes)


# ---------------------------------------------------------------------------
# 3. Retention Risk Exports
# ---------------------------------------------------------------------------
@router.get("/retention-risk.csv", summary="Export Retention Risk Scores as CSV")
def export_retention_risk_csv(
    risk_tier: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    min_probability: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_retention_risk_dataset(risk_tier=risk_tier, min_probability=min_probability, limit=limit)
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_retention_risk.csv")


@router.get("/retention-risk.json", response_model=ExportEnvelope, summary="Export Retention Risk Scores as JSON")
def export_retention_risk_json(
    risk_tier: Optional[str] = Query(None),
    min_probability: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_retention_risk_dataset(risk_tier=risk_tier, min_probability=min_probability, limit=limit)
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    params = {"risk_tier": risk_tier, "min_probability": min_probability, "limit": limit}
    return service.build_export_envelope("retention_risk", "json", data, payload_bytes, params)


# ---------------------------------------------------------------------------
# 4. Retention Interventions Exports
# ---------------------------------------------------------------------------
@router.get("/interventions.csv", summary="Export Retention Interventions as CSV")
def export_interventions_csv(
    status: Optional[str] = Query(None),
    intervention_type: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_interventions_dataset(status=status, intervention_type=intervention_type, limit=limit)
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_interventions.csv")


@router.get("/interventions.json", response_model=ExportEnvelope, summary="Export Retention Interventions as JSON")
def export_interventions_json(
    status: Optional[str] = Query(None),
    intervention_type: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_interventions_dataset(status=status, intervention_type=intervention_type, limit=limit)
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    params = {"status": status, "intervention_type": intervention_type, "limit": limit}
    return service.build_export_envelope("interventions", "json", data, payload_bytes, params)


# ---------------------------------------------------------------------------
# 5. Engagement Analytics Exports
# ---------------------------------------------------------------------------
@router.get("/engagement.csv", summary="Export Engagement Analytics as CSV")
def export_engagement_csv(
    department_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_engagement_dataset(department_id=department_id, start_date=start_date, end_date=end_date, limit=limit)
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_engagement.csv")


@router.get("/engagement.json", response_model=ExportEnvelope, summary="Export Engagement Analytics as JSON")
def export_engagement_json(
    department_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_engagement_dataset(department_id=department_id, start_date=start_date, end_date=end_date, limit=limit)
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    params = {"department_id": department_id, "start_date": str(start_date) if start_date else None, "end_date": str(end_date) if end_date else None, "limit": limit}
    return service.build_export_envelope("engagement", "json", data, payload_bytes, params)


# ---------------------------------------------------------------------------
# 6. Workload Analytics Exports
# ---------------------------------------------------------------------------
@router.get("/workload.csv", summary="Export Workload Analytics as CSV")
def export_workload_csv(
    department_id: Optional[str] = Query(None),
    is_overallocated: Optional[bool] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_workload_dataset(department_id=department_id, is_overallocated=is_overallocated, limit=limit)
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_workload.csv")


@router.get("/workload.json", response_model=ExportEnvelope, summary="Export Workload Analytics as JSON")
def export_workload_json(
    department_id: Optional[str] = Query(None),
    is_overallocated: Optional[bool] = Query(None),
    limit: int = Query(10000, ge=1, le=50000),
    session: Session = Depends(get_session),
):
    service = ExportService(session)
    data = service.get_workload_dataset(department_id=department_id, is_overallocated=is_overallocated, limit=limit)
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    params = {"department_id": department_id, "is_overallocated": is_overallocated, "limit": limit}
    return service.build_export_envelope("workload", "json", data, payload_bytes, params)


# ---------------------------------------------------------------------------
# 7. Validation Data Quality Exports
# ---------------------------------------------------------------------------
@router.get("/validation.csv", summary="Export 12-Pillar Validation as CSV")
def export_validation_csv(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_validation_dataset()
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_validation.csv")


@router.get("/validation.json", response_model=ExportEnvelope, summary="Export 12-Pillar Validation as JSON")
def export_validation_json(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_validation_dataset()
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    return service.build_export_envelope("validation", "json", data, payload_bytes)


# ---------------------------------------------------------------------------
# 8. Model Performance Exports
# ---------------------------------------------------------------------------
@router.get("/model-metrics.csv", summary="Export Model Performance Metrics as CSV")
def export_model_metrics_csv(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_model_metrics_dataset()
    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_model_metrics.csv")


@router.get("/model-metrics.json", response_model=ExportEnvelope, summary="Export Model Performance Metrics as JSON")
def export_model_metrics_json(session: Session = Depends(get_session)):
    service = ExportService(session)
    data = service.get_model_metrics_dataset()
    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    return service.build_export_envelope("model_metrics", "json", data, payload_bytes)


# ---------------------------------------------------------------------------
# 9. Restricted HR Historical Separations Export (Ground-Truth Protection)
# ---------------------------------------------------------------------------
@router.get("/historical-separations.csv", summary="Export Historical Separation Records as CSV (HR Restricted)")
def export_historical_separations_csv(
    x_hr_authorization: str = Header(default="false", alias="X-HR-Authorization"),
    session: Session = Depends(get_session),
):
    is_authorized = x_hr_authorization.lower() == "true"
    service = ExportService(session)
    try:
        data = service.get_historical_separations_dataset(is_hr_authorized=is_authorized)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    csv_str = service.format_csv(data)
    return _csv_response(csv_str, "workforceiq_historical_separations_restricted.csv")


@router.get("/historical-separations.json", response_model=ExportEnvelope, summary="Export Historical Separation Records as JSON (HR Restricted)")
def export_historical_separations_json(
    x_hr_authorization: str = Header(default="false", alias="X-HR-Authorization"),
    session: Session = Depends(get_session),
):
    is_authorized = x_hr_authorization.lower() == "true"
    service = ExportService(session)
    try:
        data = service.get_historical_separations_dataset(is_hr_authorized=is_authorized)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    payload_bytes = json.dumps(data, default=str).encode("utf-8")
    return service.build_export_envelope("historical_separations", "json", data, payload_bytes, data_classification="RESTRICTED_GROUND_TRUTH")


# ---------------------------------------------------------------------------
# 10. Executive Downloadable Report
# ---------------------------------------------------------------------------
@router.get("/reports/executive", summary="Download Executive Workforce Retention Report")
def download_executive_report(session: Session = Depends(get_session)):
    service = ExportService(session)
    return service.generate_executive_report()
