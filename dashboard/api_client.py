"""
WorkforceIQ – Unified Dashboard API Client.

Connects the Streamlit UI to:
  1. The live FastAPI REST API (http://127.0.0.1:8000).
  2. A resilient direct service fallback when the REST server is offline or running standalone.

All data structures conform to the Phase 5/6 Pydantic schemas.
"""

from datetime import date
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from altair.datasets import data
import httpx

logger = logging.getLogger("workforceiq.dashboard_client")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

API_BASE_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
HR_ANALYTICS_TOKEN = os.environ.get("HR_ANALYTICS_TOKEN", "")

ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
MANIFESTS_DIR = PROJECT_ROOT / "data" / "manifests"


class DashboardAPIClient:
    def __init__(self, base_url: str = API_BASE_URL, timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Executes an HTTP GET request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, params=params, headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"API GET {endpoint} returned {res.status_code}: {res.text}")
                return None
        except Exception as exc:
            logger.debug(f"Direct HTTP call failed for {endpoint} ({exc}); falling back to service layer.")
            return None

    def _post(self, endpoint: str, json_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Executes an HTTP POST request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=json_data, headers=headers)
                if res.status_code in [200, 201]:
                    return res.json()
                logger.warning(f"API POST {endpoint} returned {res.status_code}: {res.text}")
                return None
        except Exception as exc:
            logger.debug(f"Direct HTTP POST failed for {endpoint} ({exc}); falling back to service layer.")
            return None

    def _patch(self, endpoint: str, json_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Executes an HTTP PATCH request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            with httpx.Client(timeout=self.timeout) as client:
                res = client.patch(url, json=json_data, headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"API PATCH {endpoint} returned {res.status_code}: {res.text}")
                return None
        except Exception as exc:
            logger.debug(f"Direct HTTP PATCH failed for {endpoint} ({exc}); falling back to service layer.")
            return None

    # -----------------------------------------------------------------------
    # System Health
    # -----------------------------------------------------------------------
    def get_health(self) -> Dict[str, Any]:
        data = self._get("/health")
        if data:
            return data
        # Fallback to local DB check
        try:
            from backend.database import check_database_health
            return check_database_health()
        except Exception as e:
            return {"status": "UNHEALTHY", "error": str(e)}

    # -----------------------------------------------------------------------
    # Attrition & Retention Intelligence
    # -----------------------------------------------------------------------
    def get_attrition_summary(self) -> Dict[str, Any]:
        data = self._get("/api/v1/attrition/summary")
        if data:
            return data
        from backend.database import get_session
        from backend.services.analytics_service import get_operational_attrition_summary
        session = next(get_session())
        try:
            res = get_operational_attrition_summary(session)
            return res.model_dump() if hasattr(res, "model_dump") else res.dict()
        finally:
            session.close()

    def get_historical_attrition_trends(self) -> Dict[str, Any]:
        """Fetch historical outcomes using HR Analytics token authorization."""
        if not HR_ANALYTICS_TOKEN:
            logger.warning("HR Analytics token is not configured.")
            return {}

        headers = {"X-HR-Analytics-Token": HR_ANALYTICS_TOKEN}
        url = f"{self.base_url}/api/v1/attrition/trends"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            # Do not bypass an explicit API rejection or other HTTP error.
            logger.warning(
                "Historical attrition API returned status %s.",
                response.status_code,
            )
            return {}

        except (httpx.ConnectError, httpx.ConnectTimeout):
            # The API is unreachable (for example, standalone Streamlit/test mode).
            # Permit local access only after verifying the configured HR token.
            logger.info("API unavailable. Checking authorized local access.")

            from backend.auth import verify_hr_token
            from backend.database import get_session
            from backend.services.analytics_service import (
                get_historical_attrition_trends as get_trends,
            )

            if not verify_hr_token(
                HR_ANALYTICS_TOKEN,
                request_path="dashboard/local-historical-attrition",
            ):
                return {}

            session = next(get_session())
            try:
                result = get_trends(session, is_authorized=True)
                return (
                    result.model_dump()
                    if hasattr(result, "model_dump")
                    else result.dict()
                )
            finally:
                session.close()

        except Exception:
            logger.exception("Unable to retrieve historical attrition trends.")
            return {}

    # -----------------------------------------------------------------------
    # Departments & Headcount
    # -----------------------------------------------------------------------
    def get_departments(self) -> List[Dict[str, Any]]:
        data = self._get("/api/v1/departments")
        if data:
            return data.get("items", []) if isinstance(data, dict) else data
        from backend.database import get_session
        from backend.services.department_service import get_departments
        session = next(get_session())
        try:
            res = get_departments(session)
            return [d.model_dump() if hasattr(d, "model_dump") else d.dict() for d in res]
        finally:
            session.close()

    def get_department_detail(self, department_id: str) -> Optional[Dict[str, Any]]:
        data = self._get(f"/api/v1/departments/{department_id}")
        if data:
            return data
        from backend.database import get_session
        from backend.services.department_service import get_department_detail
        session = next(get_session())
        try:
            res = get_department_detail(session, department_id)
            return res.model_dump() if hasattr(res, "model_dump") else (res.dict() if res else None)
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Employees (Paginated & 360 Profile)
    # -----------------------------------------------------------------------
    def get_employees(
        self,
        page: int = 1,
        page_size: int = 50,
        department_id: Optional[str] = None,
        role_id: Optional[str] = None,
        status: Optional[str] = None,
        work_location: Optional[str] = None,
        risk_tier: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "employee_id",
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        if department_id:
            params["department_id"] = department_id
        if role_id:
            params["role_id"] = role_id
        if status:
            params["status"] = status
        if work_location:
            params["work_location"] = work_location
        if risk_tier:
            params["risk_tier"] = risk_tier
        if search:
            params["search"] = search

        data = self._get("/api/v1/employees", params=params)
        if data:
            if "data" in data and "items" not in data:
                data["items"] = data["data"]
            return data

        from backend.database import get_session
        from backend.services.employee_service import get_employees
        session = next(get_session())
        try:
            res = get_employees(
                session,
                page=page,
                page_size=page_size,
                department_id=department_id,
                role_id=role_id,
                status=status,
                work_location=work_location,
                risk_tier=risk_tier,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            out = res.model_dump() if hasattr(res, "model_dump") else res.dict()
            if "data" in out and "items" not in out:
                out["items"] = out["data"]
            return out
        finally:
            session.close()

    def get_employee_detail(self, employee_id: str) -> Optional[Dict[str, Any]]:
        data = self._get(f"/api/v1/employees/{employee_id}")
        if data:
            return data
        from backend.database import get_session
        from backend.services.employee_service import get_employee_detail
        session = next(get_session())
        try:
            res = get_employee_detail(session, employee_id)
            return res.model_dump() if hasattr(res, "model_dump") else (res.dict() if res else None)
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # ML Predictions & SHAP Explainability
    # -----------------------------------------------------------------------
    def get_employee_prediction(
        self,
        employee_id: str,
        as_of_date: Optional[date] = None,
        top_n_drivers: int = 5,
    ) -> Optional[Dict[str, Any]]:
        params = {"top_n_drivers": top_n_drivers}
        if as_of_date:
            params["as_of_date"] = str(as_of_date)

        data = self._get(f"/api/v1/predictions/{employee_id}", params=params)
        if data:
            return data

        from backend.database import get_session
        from backend.services.prediction_service import predict_employee_risk
        session = next(get_session())
        try:
            return predict_employee_risk(
                session=session,
                employee_id=employee_id,
                as_of_date=as_of_date,
                top_n_drivers=top_n_drivers,
            )
        except Exception as e:
            logger.warning(f"Error predicting risk for {employee_id}: {e}")
            return None
        finally:
            session.close()

    def get_model_metrics(self) -> Dict[str, Any]:
        data = self._get("/api/v1/predictions/model/metrics")
        if data:
            return data
        with open(ARTIFACTS_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def get_model_feature_importance(self) -> Dict[str, Any]:
        data = self._get("/api/v1/predictions/model/feature-importance")
        if data:
            return data
        with open(ARTIFACTS_DIR / "shap_global_importance.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def get_model_calibration(self) -> Dict[str, Any]:
        data = self._get("/api/v1/predictions/model/calibration")
        if data:
            return data
        with open(ARTIFACTS_DIR / "calibration_report.json", "r", encoding="utf-8") as f:
            return json.load(f)

    # -----------------------------------------------------------------------
    # Longitudinal Engagement & Workload Trends
    # -----------------------------------------------------------------------
    def get_engagement_trends(
        self,
        department_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        params = {}
        if department_id:
            params["department_id"] = department_id
        if start_date:
            params["start_date"] = str(start_date)
        if end_date:
            params["end_date"] = str(end_date)

        data = self._get("/api/v1/engagement/trends", params=params)
        if data:
            return data

        from backend.database import get_session
        from backend.services.analytics_service import get_engagement_trends
        session = next(get_session())
        try:
            res = get_engagement_trends(session, department_id=department_id, start_date=start_date, end_date=end_date)
            return res.model_dump() if hasattr(res, "model_dump") else res.dict()
        finally:
            session.close()

    def get_workload_analytics(
        self,
        department_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        params = {}
        if department_id:
            params["department_id"] = department_id
        if start_date:
            params["start_date"] = str(start_date)
        if end_date:
            params["end_date"] = str(end_date)

        data = self._get("/api/v1/workload/analytics", params=params)
        if data:
            return data

        from backend.database import get_session
        from backend.services.analytics_service import get_workload_analytics
        session = next(get_session())
        try:
            res = get_workload_analytics(session, department_id=department_id, start_date=start_date, end_date=end_date)
            return res.model_dump() if hasattr(res, "model_dump") else res.dict()
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Human-in-the-Loop Interventions
    # -----------------------------------------------------------------------
    def get_interventions(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        employee_id: Optional[str] = None,
        department_id: Optional[str] = None,
        intervention_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if employee_id:
            params["employee_id"] = employee_id
        if department_id:
            params["department_id"] = department_id
        if intervention_type:
            params["intervention_type"] = intervention_type

        data = self._get("/api/v1/interventions", params=params)
        if data:
            if "data" in data and "items" not in data:
                data["items"] = data["data"]
            return data

        from backend.database import get_session
        from backend.services.intervention_service import get_interventions
        session = next(get_session())
        try:
            res = get_interventions(
                session,
                page=page,
                page_size=page_size,
                status=status,
                employee_id=employee_id,
                department_id=department_id,
                intervention_type=intervention_type,
            )
            out = res.model_dump() if hasattr(res, "model_dump") else res.dict()
            if "data" in out and "items" not in out:
                out["items"] = out["data"]
            return out
        finally:
            session.close()

    def propose_intervention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        res = self._post("/api/v1/interventions", json_data=data)
        if res:
            return res
        from backend.database import get_session
        from backend.schemas.interventions import InterventionCreate
        from backend.services.intervention_service import propose_intervention
        session = next(get_session())
        try:
            obj = InterventionCreate(**data)
            created = propose_intervention(session, obj)
            return created.model_dump() if hasattr(created, "model_dump") else created.dict()
        finally:
            session.close()

    def transition_intervention(
        self,
        intervention_id: str,
        target_status: str,
        reason: str,
        actor_id: str = "USR-HR-LEAD",
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "target_status": target_status,
            "reason": reason,
            "actor_id": actor_id,
            "notes": notes,
        }
        res = self._patch(f"/api/v1/interventions/{intervention_id}/status", json_data=payload)
        if res:
            return res
        from backend.database import get_session
        from backend.schemas.interventions import InterventionStatusPatch
        from backend.services.intervention_service import transition_intervention_status
        session = next(get_session())
        try:
            patch_obj = InterventionStatusPatch(**payload)
            updated = transition_intervention_status(session, intervention_id, patch_obj)
            return updated.model_dump() if hasattr(updated, "model_dump") else updated.dict()
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Data Quality, Validation & Anomalies
    # -----------------------------------------------------------------------
    def get_validation_summary(self) -> Dict[str, Any]:
        data = self._get("/api/v1/validation/summary")
        if data:
            # Normalize response fields for backward compatibility across dashboard views
            if "status" in data and "overall_status" not in data:
                data["overall_status"] = data["status"]
            if "total_pillars_evaluated" in data and "total_pillars" not in data:
                data["total_pillars"] = data["total_pillars_evaluated"]
            if "passed_pillars_count" in data and "passed_pillars" not in data:
                data["passed_pillars"] = data["passed_pillars_count"]
            if "pillars" in data and "pillar_results" not in data:
                # If array of pillar results provided, convert to dict keyed by pillar_name for page consumption
                data["pillar_results"] = {
                    p.get("pillar_name", f"pillar_{i}"): p
                    for i, p in enumerate(data.get("pillars", []))
                }
            return data

        summary_path = MANIFESTS_DIR / "validation_summary.json"
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            from backend.services.validation_service import get_validation_summary as svc_summary
            res = svc_summary()
            data = res.model_dump() if hasattr(res, "model_dump") else res.dict()

        # Ensure bidirectional compatibility in fallback mode
        if "overall_status" in data and "status" not in data:
            data["status"] = data["overall_status"]
        elif "status" in data and "overall_status" not in data:
            data["overall_status"] = data["status"]

        if "total_pillars" in data and "total_pillars_evaluated" not in data:
            data["total_pillars_evaluated"] = data["total_pillars"]
        elif "total_pillars_evaluated" in data and "total_pillars" not in data:
            data["total_pillars"] = data["total_pillars_evaluated"]

        if "passed_pillars" in data and "passed_pillars_count" not in data:
            data["passed_pillars_count"] = data["passed_pillars"]
        elif "passed_pillars_count" in data and "passed_pillars" not in data:
            data["passed_pillars"] = data["passed_pillars_count"]

        return data

    def get_anomalies(
        self,
        page: int = 1,
        page_size: int = 50,
        anomaly_type: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
    ) -> Dict[str, Any]:
        params = {"page": page, "page_size": page_size}
        if anomaly_type:
            params["anomaly_type"] = anomaly_type
        if severity:
            params["severity"] = severity
        if is_resolved is not None:
            params["is_resolved"] = is_resolved

        data = self._get("/api/v1/validation/anomalies", params=params)
        if data:
            if "data" in data and "items" not in data:
                data["items"] = data["data"]
            return data

        from backend.database import get_session
        from backend.services.validation_service import get_anomalies
        session = next(get_session())
        try:
            res = get_anomalies(
                session,
                page=page,
                page_size=page_size,
                anomaly_type=anomaly_type,
                severity=severity,
                is_resolved=is_resolved,
            )
            out = res.model_dump() if hasattr(res, "model_dump") else res.dict()
            if "data" in out and "items" not in out:
                out["items"] = out["data"]
            return out
        finally:
            session.close()

    # -----------------------------------------------------------------------
    # Phase 8: Data Exports & Reporting Helpers
    # -----------------------------------------------------------------------
    def get_export_manifest(self) -> Dict[str, Any]:
        """Returns the export dataset catalog and metadata."""
        data = self._get("/api/v1/exports/manifest")
        if data:
            return data
        return {
            "service": "WorkforceIQ Export Service (Local Fallback)",
            "supported_formats": ["csv", "json"],
        }

    def get_export_csv(self, dataset_name: str, params: Optional[Dict[str, Any]] = None, is_hr_authorized: bool = False) -> str:
        """Retrieves raw CSV export content."""
        headers = (
            {"X-HR-Analytics-Token": HR_ANALYTICS_TOKEN}
            if is_hr_authorized and HR_ANALYTICS_TOKEN
            else None
        )
        try:
            url = f"{self.base_url}/api/v1/exports/{dataset_name}.csv"
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, params=params, headers=headers)
                if res.status_code == 200:
                    return res.text
        except Exception:
            pass

        # Fallback to local ExportService
        from backend.database import get_session
        from backend.services.export_service import ExportService
        session = next(get_session())
        try:
            svc = ExportService(session)
            if dataset_name == "employees":
                rows = svc.get_employees_dataset()
            elif dataset_name == "departments":
                rows = svc.get_departments_dataset()
            elif dataset_name == "retention-risk":
                rows = svc.get_retention_risk_dataset()
            elif dataset_name == "interventions":
                rows = svc.get_interventions_dataset()
            elif dataset_name == "engagement":
                rows = svc.get_engagement_dataset()
            elif dataset_name == "workload":
                rows = svc.get_workload_dataset()
            elif dataset_name == "validation":
                rows = svc.get_validation_dataset()
            elif dataset_name == "model-metrics":
                rows = svc.get_model_metrics_dataset()
            elif dataset_name == "historical-separations":
                if not is_hr_authorized or not HR_ANALYTICS_TOKEN:
                    raise PermissionError("Valid HR Analytics authorization is required.")
                rows = svc.get_historical_separations_dataset(is_hr_authorized=True)
            else:
                rows = []
            return svc.format_csv(rows)
        finally:
            session.close()

    def get_executive_report(self) -> Dict[str, Any]:
        """Fetches the structured executive report."""
        data = self._get("/api/v1/exports/reports/executive")
        if data:
            return data
        from backend.database import get_session
        from backend.services.export_service import ExportService
        session = next(get_session())
        try:
            svc = ExportService(session)
            return svc.generate_executive_report()
        finally:
            session.close()


# Singleton instance for dashboard pages
api_client = DashboardAPIClient()
