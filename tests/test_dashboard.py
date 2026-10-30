"""
WorkforceIQ – Automated Pytest Suite for Streamlit Dashboard & API Client (Phase 7).

Audits:
  1. Theme design tokens, risk tier badge HTML generation, and Plotly templates.
  2. Unified Dashboard API Client (both live HTTP and service fallback modes).
  3. Retrieval of operational attrition summary, historical outcomes, and departments.
  4. Employee 360 profile and paginated retrieval.
  5. ML model metrics, calibration diagnostics, and SHAP explainability data formats.
  6. Real-time employee flight-risk inference and driver mapping.
  7. 12-pillar validation summary and anomaly registry access.
  8. Human-in-the-loop intervention list and state transition payloads.
  9. Syntax and compilation integrity of all 9 dashboard pages.
"""

import ast
from pathlib import Path
import pytest

from dashboard.api_client import DashboardAPIClient, api_client
from dashboard.theme import (
    COLORS,
    create_plotly_figure,
    get_risk_badge_html,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
PAGES_DIR = DASHBOARD_DIR / "pages"


# ---------------------------------------------------------------------------
# 1. Theme, Design Tokens & Plotly Templates
# ---------------------------------------------------------------------------

def test_theme_color_tokens_exist():
    assert "primary" in COLORS
    assert "secondary" in COLORS
    assert "risk_critical" in COLORS
    assert "risk_high" in COLORS
    assert "risk_medium" in COLORS
    assert "risk_low" in COLORS


def test_risk_badge_html_generation():
    critical_badge = get_risk_badge_html("CRITICAL")
    assert "wiq-badge-critical" in critical_badge
    assert "CRITICAL" in critical_badge

    low_badge = get_risk_badge_html("low")
    assert "wiq-badge-low" in low_badge
    assert "LOW" in low_badge


def test_create_plotly_figure_defaults():
    fig = create_plotly_figure()
    assert fig is not None
    assert fig.layout.font.family == "Inter, sans-serif"


# ---------------------------------------------------------------------------
# 2. Unified Dashboard API Client & Health
# ---------------------------------------------------------------------------

def test_dashboard_client_health():
    health = api_client.get_health()
    assert isinstance(health, dict)
    assert health.get("postgresql_reachable") is True or health.get("status") in ["HEALTHY", "DEGRADED", "ONLINE"] or "database" in health


def test_dashboard_client_attrition_summary():
    summary = api_client.get_attrition_summary()
    assert isinstance(summary, dict)
    assert summary.get("total_active_workforce") > 8000
    assert "overall_attrition_risk_avg" in summary
    assert "retention_risk_breakdown" in summary


def test_dashboard_client_historical_attrition_trends():
    trends = api_client.get_historical_attrition_trends()
    assert isinstance(trends, dict)
    assert trends.get("total_historical_separations") > 500
    assert "monthly_trends" in trends
    assert len(trends["monthly_trends"]) > 0


def test_dashboard_client_departments():
    depts = api_client.get_departments()
    assert isinstance(depts, list)
    assert len(depts) >= 8
    dept_names = [d.get("name", d.get("department_id")) for d in depts]
    assert any("Engineering" in n for n in dept_names)


def test_dashboard_client_employees_paginated():
    res = api_client.get_employees(page=1, page_size=10)
    assert isinstance(res, dict)
    assert "items" in res or "data" in res
    items = res.get("items") or res.get("data")
    assert len(items) <= 10
    assert res.get("total", 0) > 8000


def test_dashboard_client_employee_detail():
    emp = api_client.get_employee_detail("EMP-000001")
    assert emp is not None
    assert emp.get("employee_id") == "EMP-000001"
    assert "first_name" in emp or "profile" in emp
    assert "compensation_history" in emp or "compensation" in emp


# ---------------------------------------------------------------------------
# 3. Model Metrics, Calibration & Predictions
# ---------------------------------------------------------------------------

def test_dashboard_client_model_metrics():
    meta = api_client.get_model_metrics()
    assert isinstance(meta, dict)
    assert meta.get("algorithm") == "RandomForest"
    assert meta.get("model_version") == "v2.0.0-prospective"
    assert meta["final_test_metrics"]["roc_auc"] > 0.80
    assert meta["final_test_metrics"]["pr_auc"] > 0.05


def test_dashboard_client_model_feature_importance():
    shap_data = api_client.get_model_feature_importance()
    assert isinstance(shap_data, dict)
    assert "ranked_features" in shap_data
    assert len(shap_data["ranked_features"]) >= 10
    top_feature = shap_data["ranked_features"][0]
    assert "human_label" in top_feature
    assert top_feature["mean_abs_shap"] > 0.0


def test_dashboard_client_model_calibration():
    calib = api_client.get_model_calibration()
    assert isinstance(calib, dict)
    assert "validation_calibration" in calib
    assert calib["validation_calibration"]["beats_dummy_baseline"] is True
    assert calib["validation_calibration"]["ece"] < 0.01


def test_dashboard_client_employee_prediction():
    pred = api_client.get_employee_prediction("EMP-000001")
    assert pred is not None
    assert "flight_risk_probability" in pred
    assert 0.0 <= pred["flight_risk_probability"] <= 1.0
    assert pred["risk_tier"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "top_risk_drivers" in pred
    assert "top_protective_factors" in pred
    assert "responsible_ai_disclaimer" in pred


# ---------------------------------------------------------------------------
# 4. Data Quality & Interventions
# ---------------------------------------------------------------------------

def test_dashboard_client_validation_summary():
    val = api_client.get_validation_summary()
    assert isinstance(val, dict)
    # Check both canonical and backward-compatible fields
    assert val.get("overall_status") == "PASSED"
    assert val.get("status") == "PASSED"
    assert val.get("passed_pillars") == 12
    assert val.get("passed_pillars_count") == 12
    assert val.get("total_pillars") == 12
    assert val.get("total_pillars_evaluated") == 12


def test_dashboard_client_validation_summary_api_contract_normalization():
    """Verify that raw REST API response format with 'status' is properly normalized."""
    client = DashboardAPIClient()
    mock_api_payload = {
        "status": "PASSED",
        "evaluated_at": "2026-10-30T16:00:00Z",
        "total_pillars_evaluated": 12,
        "passed_pillars_count": 12,
        "failed_pillars_count": 0,
        "total_violations_count": 0,
        "pillars": [
            {"pillar_name": "1_primary_key_uniqueness", "status": "PASSED", "total_checks": 14, "violations_count": 0}
        ],
        "recent_anomalies": [],
    }
    client._get = lambda endpoint: mock_api_payload.copy()
    result = client.get_validation_summary()
    assert result["status"] == "PASSED"
    assert result["overall_status"] == "PASSED"
    assert result["passed_pillars"] == 12
    assert result["total_pillars"] == 12
    assert "pillar_results" in result
    assert "1_primary_key_uniqueness" in result["pillar_results"]


def test_dashboard_client_interventions():
    ints = api_client.get_interventions(page=1, page_size=10)
    assert isinstance(ints, dict)
    assert "items" in ints or "data" in ints
    items = ints.get("items") or ints.get("data")
    assert isinstance(items, list)


# ---------------------------------------------------------------------------
# 5. Compilation & Syntax Verification of All Dashboard Pages
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("page_file", [
    DASHBOARD_DIR / "app.py",
    DASHBOARD_DIR / "theme.py",
    DASHBOARD_DIR / "api_client.py",
    PAGES_DIR / "1_Executive_Overview.py",
    PAGES_DIR / "2_Workforce_Analytics.py",
    PAGES_DIR / "3_Retention_Intelligence.py",
    PAGES_DIR / "4_Individual_Employee_Insights.py",
    PAGES_DIR / "5_Intervention_Management.py",
    PAGES_DIR / "6_Engagement_Analytics.py",
    PAGES_DIR / "7_Workload_Analytics.py",
    PAGES_DIR / "8_Data_Quality_and_Validation.py",
    PAGES_DIR / "9_Model_Performance_and_Explainability.py",
])
def test_dashboard_page_syntax_and_compilation(page_file):
    """Parses AST for every dashboard script to ensure zero syntax or import structure errors."""
    assert page_file.exists(), f"File {page_file} does not exist"
    with open(page_file, "r", encoding="utf-8") as f:
        source_code = f.read()
    parsed_ast = ast.parse(source_code, filename=str(page_file))
    assert parsed_ast is not None
