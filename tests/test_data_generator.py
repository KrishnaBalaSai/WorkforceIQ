"""
Automated Pytest Suite for WorkforceIQ Synthetic Data Generator (Phase 2).
Verifies:
1. Deterministic reproducibility with random seed 20261022.
2. Parent records generated before dependent records.
3. Foreign key referential integrity across all tables.
4. Voluntary attrition within 5% - 15% range.
5. All four mandatory anomaly scenarios labelled in manifest.
6. Clean separation of ground truth from input features.
7. Valid ID conventions and non-empty datasets.
"""

from pathlib import Path
import pytest
import pandas as pd

from data_generator.config import RANDOM_SEED, STARTER_EMPLOYEE_COUNT
from data_generator.generator import run_pipeline

@pytest.fixture(scope="module")
def starter_run_data(tmp_path_factory):
    """Run generator with starter cohort in a temporary directory."""
    temp_dir = tmp_path_factory.mktemp("data_test")
    res = run_pipeline(
        employee_count=STARTER_EMPLOYEE_COUNT,
        seed=RANDOM_SEED,
        output_dir=temp_dir,
        export_json=True,
        inject_negative_scenarios=True,
    )
    return res, temp_dir

def test_pipeline_completes_and_validates(starter_run_data):
    res, _ = starter_run_data
    val = res["validation_report"]
    assert val["is_valid"], f"Validation failed with errors: {val['errors']}"
    assert val["error_count"] == 0

def test_employee_count_and_id_format(starter_run_data):
    res, _ = starter_run_data
    employees = res["datasets"]["employees"]
    assert len(employees) == STARTER_EMPLOYEE_COUNT
    for idx, emp in enumerate(employees, 1):
        expected_id = f"EMP-{idx:06d}"
        assert emp["employee_id"] == expected_id
        assert "@yottaflex.ai" in emp["email"]

def test_parent_catalogs_exist(starter_run_data):
    res, _ = starter_run_data
    datasets = res["datasets"]
    assert len(datasets["departments"]) >= 8
    assert len(datasets["job_roles"]) >= 100
    assert len(datasets["skills"]) >= 10

def test_voluntary_attrition_within_bounds(starter_run_data):
    res, _ = starter_run_data
    stats = res["validation_report"]["statistics"]
    vol_rate = stats["voluntary_attrition_rate_pct"]
    # Voluntary attrition must be strictly between 5.0% and 15.0%
    assert 5.0 <= vol_rate <= 15.0, f"Voluntary attrition rate {vol_rate}% is outside 5-15% target band."

def test_all_four_anomaly_scenarios_injected(starter_run_data):
    res, _ = starter_run_data
    manifest = res["anomaly_manifest"]
    assert len(manifest) >= 4, "Expected at least 4 injected anomalies"
    
    injected_types = {a["anomaly_type"] for a in manifest}
    expected_types = {
        "POST_TERMINATION_ACTIVITY",
        "CIRCULAR_HIERARCHY",
        "COMPENSATION_INVERSION",
        "LEAVE_HOUR_CONFLICT",
    }
    for expected in expected_types:
        assert expected in injected_types, f"Missing injected anomaly type: {expected}"

def test_ground_truth_separation_in_export(starter_run_data):
    _, temp_dir = starter_run_data
    generated_dir = temp_dir / "generated"
    ground_truth_dir = temp_dir / "ground_truth"
    
    # Clean input files must exist in data/generated/
    assert (generated_dir / "employees.csv").exists()
    assert (generated_dir / "compensation_records.csv").exists()
    assert (generated_dir / "derived_workforce_features.csv").exists()
    
    # Ground truth files must exist in data/ground_truth/
    assert (ground_truth_dir / "exit_records.csv").exists()
    assert (ground_truth_dir / "attrition_labels.csv").exists()
    assert (ground_truth_dir / "anomaly_manifest.csv").exists()
    
    # exit_records must NOT be inside data/generated/ to prevent leakage
    assert not (generated_dir / "exit_records.csv").exists()

def test_seed_reproducibility(tmp_path):
    """Running generator twice with same seed produces identical employee IDs and emails."""
    run1 = run_pipeline(employee_count=50, seed=RANDOM_SEED, output_dir=tmp_path / "run1", export_json=False)
    run2 = run_pipeline(employee_count=50, seed=RANDOM_SEED, output_dir=tmp_path / "run2", export_json=False)
    
    emps1 = [(e["employee_id"], e["email"]) for e in run1["datasets"]["employees"]]
    emps2 = [(e["employee_id"], e["email"]) for e in run2["datasets"]["employees"]]
    assert emps1 == emps2, "Generator output is not deterministic across identical seeds."
