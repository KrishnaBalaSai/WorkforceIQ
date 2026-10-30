"""
WorkforceIQ – Automated Pytest Suite for Machine Learning and Explainability Pipeline (Phase 6).

Audits:
  1. Feature anti-leakage isolation (no status flags, exit records, or future data).
  2. Competing-risk censoring (involuntary separations and retirements properly censored).
  3. Strict chronological prospective temporal split ordering.
  4. Model artifact existence, schema validation, and persistence integrity.
  5. Probability calibration quality (Brier score beats dummy prior, ECE < 0.01).
  6. Validation-only threshold optimization and out-of-sample test evaluation.
  7. Global and individual SHAP explainability with human-readable mappings.
  8. Mandatory Responsible AI guardrails and advisory disclaimers.
  9. REST API prediction and metadata endpoint compliance.
"""

from datetime import date
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from ml.explainability import (
    FEATURE_LABEL_MAP,
    RESPONSIBLE_AI_DISCLAIMER,
    compute_individual_explanation,
    get_human_label,
    get_risk_tier,
    load_model_artifacts,
)
from ml.features import (
    CATEGORICAL_FEATURES,
    EXCLUDED_COLUMNS,
    NUMERIC_FEATURES,
    TEST_PREDICTION_DATES,
    TRAIN_PREDICTION_DATES,
    VAL_PREDICTION_DATES,
    compute_point_in_time_features,
    get_feature_names,
    get_prospective_temporal_splits,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"


# ---------------------------------------------------------------------------
# 1. Feature Anti-Leakage & Governance
# ---------------------------------------------------------------------------

def test_no_excluded_columns_in_feature_matrix():
    """Confirms that none of the prohibited status flags or exit columns appear in feature lists."""
    manifest = get_feature_names()
    all_features = set(manifest["all_features"])
    excluded = set(manifest["excluded"])

    overlap = all_features.intersection(excluded)
    assert len(overlap) == 0, f"Prohibited leakage columns found in active feature set: {overlap}"


def test_point_in_time_feature_matrix_leakage_isolation():
    """Extracts features for a training cohort and verifies zero presence of exit or status columns."""
    X, y, groups = compute_point_in_time_features("2024-12-15", horizon_days=90)
    for col in EXCLUDED_COLUMNS:
        assert col not in X.columns, f"Prohibited column '{col}' leaked into feature matrix X"
    assert "actual_attrition" not in X.columns
    assert "status" not in X.columns
    assert "is_active" not in X.columns


def test_feature_manifest_file_matches_implementation():
    """Checks that ml/artifacts/feature_schema.json matches registered feature lists."""
    schema_path = ARTIFACTS_DIR / "feature_schema.json"
    assert schema_path.exists(), "feature_schema.json does not exist in ml/artifacts/"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert set(schema["numeric_features"]) == set(NUMERIC_FEATURES)
    assert set(schema["categorical_features"]) == set(CATEGORICAL_FEATURES)
    assert len(schema["transformed_feature_names"]) >= len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)


# ---------------------------------------------------------------------------
# 2. Competing-Risk Censoring
# ---------------------------------------------------------------------------

def test_competing_risk_censoring_reduces_population_correctly():
    """
    Verifies that enabling competing-risk censoring correctly excludes employees who
    experience non-voluntary departures (involuntary termination or retirement) during the horizon.
    """
    X_censored, y_censored, _ = compute_point_in_time_features("2025-03-15", horizon_days=90, censor_competing_risks=True)
    X_uncensored, y_uncensored, _ = compute_point_in_time_features("2025-03-15", horizon_days=90, censor_competing_risks=False)

    # Censored population must be smaller than uncensored population
    censored_count = len(X_uncensored) - len(X_censored)
    assert censored_count > 0, "Competing-risk censoring did not exclude any non-voluntary departures"
    assert y_censored.sum() == y_uncensored.sum(), "Voluntary exit count must remain identical under competing-risk censoring"


# ---------------------------------------------------------------------------
# 3. Prospective Temporal Ordering
# ---------------------------------------------------------------------------

def test_temporal_split_chronological_ordering():
    """Verifies that all training dates strictly precede validation date, and validation precedes test date."""
    train_dates = [pd.to_datetime(d) for d in TRAIN_PREDICTION_DATES]
    val_date = pd.to_datetime(VAL_PREDICTION_DATES[0])
    test_date = pd.to_datetime(TEST_PREDICTION_DATES[0])

    for t_dt in train_dates:
        assert t_dt < val_date, f"Train date {t_dt} is not strictly before validation date {val_date}"
    assert val_date < test_date, f"Validation date {val_date} is not strictly before test date {test_date}"


def test_disjoint_prediction_horizons():
    """Verifies that consecutive training prediction dates do not have overlapping 90-day outcome windows."""
    dates = [pd.to_datetime(d) for d in TRAIN_PREDICTION_DATES + VAL_PREDICTION_DATES + TEST_PREDICTION_DATES]
    for i in range(len(dates) - 1):
        delta_days = (dates[i + 1] - dates[i]).days
        assert delta_days >= 89, f"Prediction dates {dates[i]} and {dates[i+1]} overlap within 90 days ({delta_days} days apart)"


# ---------------------------------------------------------------------------
# 4. Artifact Existence & Integrity
# ---------------------------------------------------------------------------

def test_all_model_artifacts_exist():
    """Audits the presence of all 9 required model and explainability artifacts."""
    required_files = [
        "best_model.joblib",
        "raw_classifier.joblib",
        "preprocessor.joblib",
        "feature_schema.json",
        "model_metadata.json",
        "calibration_report.json",
        "shap_global_importance.json",
        "shap_sample_explanations.json",
        "shap_summary.png",
    ]
    for fname in required_files:
        p = ARTIFACTS_DIR / fname
        assert p.exists(), f"Required artifact '{fname}' missing from ml/artifacts/"
        assert p.stat().st_size > 0, f"Artifact '{fname}' is empty (0 bytes)"


def test_model_metadata_structure_and_completeness():
    """Validates the schema and completeness of ml/artifacts/model_metadata.json."""
    with open(ARTIFACTS_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_version"] == "v2.0.0-prospective"
    assert meta["algorithm"] == "RandomForest"
    assert "time_aware_cv_metrics" in meta
    assert "validation_comparison" in meta
    assert "threshold_optimization" in meta
    assert "calibrated_validation_metrics" in meta
    assert "final_test_metrics" in meta
    assert "calibration_quality" in meta


# ---------------------------------------------------------------------------
# 5. Probability Calibration Quality
# ---------------------------------------------------------------------------

def test_calibration_beats_dummy_prevalence_baseline():
    """
    Confirms that the Platt-calibrated model achieves a Brier score strictly lower than
    a naive prevalence-based dummy baseline on both Validation and Test cohorts.
    """
    with open(ARTIFACTS_DIR / "calibration_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    val_cal = report["validation_calibration"]
    test_cal = report["test_calibration"]

    assert val_cal["beats_dummy_baseline"] is True, "Validation calibrated Brier score failed to beat dummy prior"
    assert test_cal["beats_dummy_baseline"] is True, "Test calibrated Brier score failed to beat dummy prior"

    # ECE must be strictly below 1% (0.01)
    assert val_cal["ece"] < 0.01, f"Validation ECE {val_cal['ece']} exceeds 0.01"
    assert test_cal["ece"] < 0.01, f"Test ECE {test_cal['ece']} exceeds 0.01"


def test_calibrated_probabilities_bounded_in_unit_interval():
    """Ensures calibrator outputs probabilities strictly within [0.0, 1.0]."""
    calibrator = joblib.load(ARTIFACTS_DIR / "best_model.joblib")
    test_inputs = np.array([[0.0], [0.1], [0.3], [0.5], [0.8], [1.0]])
    probs = calibrator.predict_proba(test_inputs)[:, 1]

    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)
    # Monotonicity: higher raw probability must yield higher calibrated probability
    assert np.all(np.diff(probs) >= 0.0)


# ---------------------------------------------------------------------------
# 6. Validation-Only Threshold Optimization
# ---------------------------------------------------------------------------

def test_selected_threshold_properties():
    """Verifies that the chosen threshold flags an actionable ~5-7% of workforce and achieves non-zero test metrics."""
    with open(ARTIFACTS_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    thresh = meta["threshold_optimization"]["selected_operational_threshold"]
    assert 0.030 <= thresh <= 0.070, f"Selected threshold {thresh} is outside the sound operational range"

    test_metrics = meta["final_test_metrics"]
    assert test_metrics["precision"] > 0.05, f"Test precision {test_metrics['precision']} is below 5%"
    assert test_metrics["recall"] > 0.20, f"Test recall {test_metrics['recall']} is below 20%"
    assert test_metrics["f1"] > 0.10, f"Test F1 {test_metrics['f1']} is below 0.10"
    assert test_metrics["confusion_matrix"]["true_positives"] > 0


# ---------------------------------------------------------------------------
# 7. SHAP Explainability & Human Labels
# ---------------------------------------------------------------------------

def test_global_shap_importance_values():
    """Verifies global SHAP importance ranks features and contains human-readable labels."""
    with open(ARTIFACTS_DIR / "shap_global_importance.json", "r", encoding="utf-8") as f:
        shap_data = json.load(f)

    ranked = shap_data["ranked_features"]
    assert len(ranked) > 10
    assert ranked[0]["mean_abs_shap"] > ranked[-1]["mean_abs_shap"]
    assert "human_label" in ranked[0]
    assert RESPONSIBLE_AI_DISCLAIMER in shap_data["responsible_ai_disclaimer"]


def test_individual_explanation_structure():
    """Computes an individual explanation on a sample row and audits the resulting schema."""
    prep, raw_clf, calibrator, feature_names, _ = load_model_artifacts()

    # Create dummy sample row
    sample_df = pd.DataFrame([{
        "grade_level": 3,
        "tenure_months": 24.0,
        "base_salary": 110000.0,
        "compa_ratio": 0.95,
        "promotions_count": 1,
        "avg_job_satisfaction": 2.5,
        "avg_work_life_balance": 2.2,
        "latest_burnout_risk": 0.85,
        "latest_sentiment_score": -0.65,
        "avg_weekly_logged_hours": 55.0,
        "department_id": "DEP-ENG-01",
        "work_location": "REMOTE",
        "employment_type": "FULL_TIME",
    }])

    expl = compute_individual_explanation("EMP-TEST-01", sample_df)

    assert "flight_risk_probability" in expl
    assert "risk_tier" in expl
    assert expl["risk_tier"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(expl["top_risk_drivers"]) > 0
    assert len(expl["top_protective_factors"]) > 0
    assert RESPONSIBLE_AI_DISCLAIMER in expl["responsible_ai_disclaimer"]


# ---------------------------------------------------------------------------
# 8. REST API Endpoints
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


def test_api_model_metrics(api_client):
    res = api_client.get("/api/v1/predictions/model/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "RandomForest"
    assert data["final_test_metrics"]["roc_auc"] > 0.80


def test_api_feature_importance(api_client):
    res = api_client.get("/api/v1/predictions/model/feature-importance")
    assert res.status_code == 200
    data = res.json()
    assert len(data["ranked_features"]) > 0
    assert "Sentiment Score" in data["ranked_features"][0]["human_label"] or data["ranked_features"][0]["mean_abs_shap"] > 0


def test_api_calibration_report(api_client):
    res = api_client.get("/api/v1/predictions/model/calibration")
    assert res.status_code == 200
    data = res.json()
    assert data["validation_calibration"]["beats_dummy_baseline"] is True


def test_api_employee_prediction(api_client):
    res = api_client.get("/api/v1/predictions/EMP-000001")
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == "EMP-000001"
    assert 0.0 <= data["flight_risk_probability"] <= 1.0
    assert data["risk_tier"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(data["top_risk_drivers"]) > 0
    assert "statistical associations" in data["responsible_ai_disclaimer"]


def test_api_employee_not_found(api_client):
    res = api_client.get("/api/v1/predictions/EMP-NONEXISTENT")
    assert res.status_code == 404
