"""
Automated Pytest Suite for Phase 3: Ground Truth and Anomaly Verification.
Tests the four mandatory challenge verification scenarios:
1. Future information leakage into model features.
2. Missing engagement survey incorrectly treated as negative.
3. Attrition outcome inconsistent with termination date.
4. Individual score used without explanation or human review.
And verifies:
- All 148 anomalies have unique identifiers.
- Every anomaly has a corresponding ground-truth record.
- Ground truth is not included in clean model input features.
- Normal records remain unaffected.
"""

from pathlib import Path
import pytest
import pandas as pd

from validation.anomaly_verifier import run_anomaly_verification

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@pytest.fixture(scope="module")
def verification_report():
    return run_anomaly_verification(DATA_DIR)

# -----------------------------------------------------------------------------
# Core Anomaly Manifest & Identifier Checks
# -----------------------------------------------------------------------------
def test_all_148_anomalies_have_unique_identifiers(verification_report):
    metrics = verification_report["manifest_metrics"]
    assert metrics["total_anomalies"] == 148, f"Expected 148 anomalies, found {metrics['total_anomalies']}"
    assert metrics["unique_anomaly_ids"] == 148
    assert metrics["all_ids_unique"] is True

def test_every_anomaly_has_valid_target_record(verification_report):
    metrics = verification_report["manifest_metrics"]
    assert metrics["target_employees_valid"] is True
    # Verify all 4 types exist in manifest
    type_counts = metrics["type_counts"]
    assert type_counts.get("POST_TERMINATION_ACTIVITY", 0) == 45
    assert type_counts.get("CIRCULAR_HIERARCHY", 0) == 13
    assert type_counts.get("COMPENSATION_INVERSION", 0) == 50
    assert type_counts.get("LEAVE_HOUR_CONFLICT", 0) == 40

# -----------------------------------------------------------------------------
# Scenario 1: Future Information Leakage Into Model Features
# -----------------------------------------------------------------------------
def test_scenario_1_future_information_leakage(verification_report):
    res = verification_report["scenario_1_leakage"]
    assert res["status"] == "PASSED"
    assert len(res["leakage_columns_found"]) == 0, f"Found leaking columns: {res['leakage_columns_found']}"
    assert res["clean_features_count"] == 13
    assert len(res["verified_sample"]) >= 3

# -----------------------------------------------------------------------------
# Scenario 2: Missing Engagement Survey Incorrectly Treated as Negative
# -----------------------------------------------------------------------------
def test_scenario_2_missing_survey_negative_bias(verification_report):
    res = verification_report["scenario_2_missing_survey"]
    assert res["status"] == "PASSED"
    assert res["has_negative_bias"] is False
    assert res["derived_avg_satisfaction_mean"] >= 3.0

# -----------------------------------------------------------------------------
# Scenario 3: Attrition Outcome Inconsistent With Termination Date
# -----------------------------------------------------------------------------
def test_scenario_3_attrition_outcome_consistency(verification_report):
    res = verification_report["scenario_3_attrition_consistency"]
    assert res["status"] == "PASSED"
    assert res["separation_before_hire_violations"] == 0
    assert res["active_employees_with_exit_records"] == 0
    assert res["total_exit_records"] == 1187

# -----------------------------------------------------------------------------
# Scenario 4: Individual Score Used Without Explanation or Human Review
# -----------------------------------------------------------------------------
def test_scenario_4_score_explanation_and_hitl(verification_report):
    res = verification_report["scenario_4_score_explanation"]
    assert res["status"] == "PASSED"
    assert res["unexplained_risk_scores"] == 0
    assert res["total_risk_scores"] == 71714
    assert res["unreviewed_interventions"] == 0
    assert res["total_interventions"] == 1695

# -----------------------------------------------------------------------------
# Clean Control Group Integrity & Ground Truth Isolation
# -----------------------------------------------------------------------------
def test_ground_truth_isolated_from_clean_features(verification_report):
    checks = verification_report["integrity_checks"]
    assert checks["ground_truth_files_separated"] is True
    assert (DATA_DIR / "ground_truth" / "exit_records.csv").exists()
    assert (DATA_DIR / "ground_truth" / "attrition_labels.csv").exists()
    assert not (DATA_DIR / "generated" / "exit_records.csv").exists()

def test_normal_records_remain_unaffected(verification_report):
    checks = verification_report["integrity_checks"]
    assert checks["clean_employees_unaffected"] is True
    assert checks["total_clean_employees"] > 9800
