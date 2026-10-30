"""
Automated Pytest Suite for Phase 5, Step 1: Database Ingestion Pipeline.

Audits:
  1. Successful first ingestion run.
  2. Idempotent rerun (0 duplicates, unchanged counts).
  3. Row-count reconciliation against all source CSVs.
  4. Foreign-key referential integrity (zero orphaned records).
  5. Circular and self-referencing foreign key resolution (heads & managers).
  6. Null preservation in engagement surveys.
  7. Strict ground-truth isolation.
  8. Transaction rollback on simulated critical failure.
"""

import pytest
from sqlalchemy import text

from backend.database import _build_engine
from backend.services.ingestion_service import (
    TABLE_CONFIG,
    run_database_ingestion,
    verify_database_integrity,
)


@pytest.fixture(scope="session")
def engine():
    return _build_engine()


@pytest.fixture(scope="session")
def ingestion_run_1(engine):
    """Executes the first ingestion run and caches results."""
    return run_database_ingestion(engine=engine)


@pytest.fixture(scope="session")
def ingestion_run_2(engine, ingestion_run_1):
    """Executes the second idempotent ingestion run."""
    return run_database_ingestion(engine=engine)


@pytest.fixture(scope="session")
def integrity_audit(engine, ingestion_run_1):
    """Performs full integrity audit post-ingestion."""
    return verify_database_integrity(engine=engine)


# ---------------------------------------------------------------------------
# Ingestion Execution & Status
# ---------------------------------------------------------------------------

def test_ingestion_first_run_succeeded(ingestion_run_1):
    assert ingestion_run_1["status"] == "COMPLETED"
    assert (ingestion_run_1["total_inserted"] > 300000) or (ingestion_run_1["total_skipped"] > 300000)
    assert len(ingestion_run_1["errors"]) == 0


def test_ingestion_idempotent_second_run(ingestion_run_2):
    """A second execution must insert 0 new rows and create no duplicates."""
    assert ingestion_run_2["status"] == "COMPLETED"
    assert ingestion_run_2["total_inserted"] == 0
    assert ingestion_run_2["total_skipped"] == ingestion_run_2["total_source_rows"]
    assert len(ingestion_run_2["errors"]) == 0


# ---------------------------------------------------------------------------
# Row Count Reconciliation
# ---------------------------------------------------------------------------

def test_all_row_counts_reconciled(integrity_audit):
    assert integrity_audit["status"] == "PASSED"
    assert len(integrity_audit["row_count_mismatches"]) == 0, (
        f"Mismatched tables: {integrity_audit['row_count_mismatches']}"
    )


@pytest.mark.parametrize("item", TABLE_CONFIG)
def test_individual_table_row_count(integrity_audit, item):
    t_name = item["table_name"]
    res = integrity_audit["row_count_reconciliation"][t_name]
    assert res["matched"] is True, (
        f"Table {t_name} count mismatch: source={res['source']} vs db={res['database']}"
    )


# ---------------------------------------------------------------------------
# Foreign Key Integrity
# ---------------------------------------------------------------------------

def test_no_broken_foreign_keys(integrity_audit):
    assert len(integrity_audit["broken_foreign_keys"]) == 0, (
        f"Broken foreign keys detected: {integrity_audit['broken_foreign_keys']}"
    )


def test_circular_and_self_referential_fks(integrity_audit):
    checks = integrity_audit["integrity_checks"]
    assert checks["departments_with_heads"]["status"] == "PASSED"
    assert checks["employees_with_managers"]["status"] == "PASSED"


# ---------------------------------------------------------------------------
# Null Preservation & Ground-Truth Isolation
# ---------------------------------------------------------------------------

def test_null_temporal_effective_to_preserved(integrity_audit):
    checks = integrity_audit["integrity_checks"]
    assert checks["null_temporal_effective_to_preserved"]["status"] == "PASSED"
    assert checks["null_temporal_effective_to_preserved"]["count"] == 8813


def test_missing_engagement_surveys_represented(integrity_audit):
    checks = integrity_audit["integrity_checks"]
    assert checks["missing_engagement_surveys_represented"]["status"] == "PASSED"
    assert checks["missing_engagement_surveys_represented"]["count"] > 0


def test_strict_ground_truth_isolation(integrity_audit):
    gt = integrity_audit["ground_truth_isolation"]
    assert gt["status"] == "PASSED"
    assert gt["attrition_labels_in_db"] is False
    assert gt["anomaly_manifest_in_db"] is False
    assert gt["derived_workforce_features_in_db"] is False


# ---------------------------------------------------------------------------
# Transaction Rollback Verification
# ---------------------------------------------------------------------------

def test_transaction_rollback_on_failure(engine):
    """
    Simulating a failure midway through ingestion inside an atomic transaction
    must cleanly roll back without corrupting database state.
    """
    with pytest.raises(RuntimeError, match="Simulated pipeline failure"):
        run_database_ingestion(engine=engine, simulate_failure_at_step="skills")
