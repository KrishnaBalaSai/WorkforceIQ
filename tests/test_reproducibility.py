"""
tests/test_reproducibility.py
==============================
Pytest test suite for Phase 4: Reproducibility Validation.

Runs the WorkforceIQ data generator twice using seed 20261022 in isolated
temporary directories and verifies that both outputs are bit-for-bit identical
across:

  - Record counts for every dataset table (CSV rows).
  - SHA-256 checksums for every exported file.
  - Sampled generated IDs (employees, exit records, compensation records).
  - Dataset-level statistics (salary mean/std, attrition rate, sentiment mean).

The generator is invoked with employee_count=150 (starter mode) to keep
test execution time under 120 s while exercising the full pipeline.
"""

import pytest
from pathlib import Path
from validation.reproducibility import run_reproducibility_check


# ---------------------------------------------------------------------------
# Fixture: run the reproducibility check once for the whole module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def repro_result():
    """
    Executes run_reproducibility_check() with seed 20261022, employee_count=150.
    Results are cached at module scope to avoid running the pipeline 4x.
    """
    return run_reproducibility_check(
        employee_count=150,
        seed=20261022,
        export_report=True,
    )


# ---------------------------------------------------------------------------
# Overall verdict
# ---------------------------------------------------------------------------

class TestReproducibilityOverall:
    def test_runs_complete_without_error(self, repro_result):
        """Both pipeline runs must finish and produce a comparison result."""
        assert "reproducible" in repro_result, (
            "Reproducibility check did not return a 'reproducible' key — run may have crashed"
        )

    def test_fully_reproducible(self, repro_result):
        """The overall reproducibility verdict must be True."""
        assert repro_result["reproducible"] is True, (
            "Generator outputs were NOT identical across two runs with the same seed. "
            f"Checksum mismatches: {repro_result['checksum_comparison']['mismatches']}  "
            f"Count mismatches: {repro_result['record_count_comparison']['mismatches']}"
        )

    def test_seed_matches_requirement(self, repro_result):
        """Seed used in the reproducibility check must be 20261022."""
        assert repro_result["seed"] == 20261022

    def test_employee_count_is_consistent(self, repro_result):
        assert repro_result["employee_count"] == 150

    def test_report_file_written(self):
        report_path = (
            Path(__file__).resolve().parent.parent
            / "data" / "manifests" / "reproducibility_report.json"
        )
        assert report_path.exists(), (
            f"reproducibility_report.json was not written to {report_path}"
        )


# ---------------------------------------------------------------------------
# SHA-256 Checksum Comparison
# ---------------------------------------------------------------------------

class TestChecksumComparison:
    def test_no_checksum_mismatches(self, repro_result):
        mismatches = repro_result["checksum_comparison"]["mismatches"]
        failed_files = [
            d["file"] for d in repro_result["checksum_comparison"]["details"]
            if not d["match"]
        ]
        assert mismatches == 0, (
            f"{mismatches} file(s) have different SHA-256 checksums between runs: "
            f"{failed_files}"
        )

    def test_all_files_present_in_both_runs(self, repro_result):
        details = repro_result["checksum_comparison"]["details"]
        missing = [
            d["file"] for d in details
            if d["run_1_sha256"] == "MISSING" or d["run_2_sha256"] == "MISSING"
        ]
        assert missing == [], f"Files missing from one run: {missing}"

    def test_checksum_files_compared_count(self, repro_result):
        """Must compare at least 15 CSV files."""
        compared = repro_result["checksum_comparison"]["files_compared"]
        assert compared >= 15, (
            f"Only {compared} files compared — expected at least 15 CSVs"
        )

    def test_checksum_matches_equals_compared(self, repro_result):
        cc = repro_result["checksum_comparison"]
        assert cc["matches"] == cc["files_compared"], (
            f"Matches ({cc['matches']}) != files compared ({cc['files_compared']})"
        )

    def test_employees_csv_checksum_match(self, repro_result):
        """employees.csv must be identical between runs."""
        details = repro_result["checksum_comparison"]["details"]
        target = next(
            (d for d in details if d["file"].endswith("employees.csv")), None
        )
        assert target is not None, "employees.csv not found in checksum comparison"
        assert target["match"] is True, (
            f"employees.csv checksum mismatch: "
            f"run1={target['run_1_sha256']}, run2={target['run_2_sha256']}"
        )

    def test_exit_records_csv_checksum_match(self, repro_result):
        """exit_records.csv must be identical between runs."""
        details = repro_result["checksum_comparison"]["details"]
        target = next(
            (d for d in details if d["file"].endswith("exit_records.csv")), None
        )
        assert target is not None, "exit_records.csv not found in checksum comparison"
        assert target["match"] is True, (
            f"exit_records.csv checksum mismatch: "
            f"run1={target['run_1_sha256']}, run2={target['run_2_sha256']}"
        )


# ---------------------------------------------------------------------------
# Record Count Comparison
# ---------------------------------------------------------------------------

class TestRecordCountComparison:
    def test_no_count_mismatches(self, repro_result):
        mismatches = repro_result["record_count_comparison"]["mismatches"]
        failed = [
            d["file"] for d in repro_result["record_count_comparison"]["details"]
            if not d["match"]
        ]
        assert mismatches == 0, (
            f"{mismatches} table(s) have different row counts between runs: {failed}"
        )

    def test_count_tables_compared_count(self, repro_result):
        compared = repro_result["record_count_comparison"]["tables_compared"]
        assert compared >= 15, (
            f"Only {compared} tables compared — expected at least 15"
        )

    def test_employees_count_matches(self, repro_result):
        details = repro_result["record_count_comparison"]["details"]
        target = next(
            (d for d in details if d["file"].endswith("employees.csv")), None
        )
        assert target is not None, "employees.csv not in count comparison"
        assert target["match"] is True
        assert target["run_1_rows"] == 150
        assert target["run_2_rows"] == 150

    def test_all_counts_positive(self, repro_result):
        """Every table must have at least one data row in both runs."""
        for d in repro_result["record_count_comparison"]["details"]:
            # Skip the dataset_manifest.json counts (it's not a data table)
            if "manifest" in d["file"]:
                continue
            assert d["run_1_rows"] >= 0, f"{d['file']} has {d['run_1_rows']} rows in run 1"
            assert d["run_2_rows"] >= 0, f"{d['file']} has {d['run_2_rows']} rows in run 2"


# ---------------------------------------------------------------------------
# Generated ID Comparison
# ---------------------------------------------------------------------------

class TestIDComparison:
    def test_all_entity_ids_match(self, repro_result):
        for entity, detail in repro_result["id_comparison"].items():
            assert detail["match"] is True, (
                f"Sampled {entity} IDs differ between runs. "
                f"Run1: {detail['run_1_sample'][:3]}  "
                f"Run2: {detail['run_2_sample'][:3]}"
            )

    def test_employee_ids_match(self, repro_result):
        emp = repro_result["id_comparison"].get("employees")
        assert emp is not None, "employees not in ID comparison"
        assert emp["match"] is True, (
            f"Employee IDs differ: {emp['run_1_sample'][:3]} vs {emp['run_2_sample'][:3]}"
        )

    def test_compensation_ids_match(self, repro_result):
        comp = repro_result["id_comparison"].get("compensation_records")
        assert comp is not None, "compensation_records not in ID comparison"
        assert comp["match"] is True

    def test_exit_record_ids_match(self, repro_result):
        exits = repro_result["id_comparison"].get("exit_records")
        assert exits is not None, "exit_records not in ID comparison"
        assert exits["match"] is True


# ---------------------------------------------------------------------------
# Statistical Metrics Comparison
# ---------------------------------------------------------------------------

class TestStatisticsComparison:
    def test_all_statistics_match(self, repro_result):
        assert repro_result["statistics_comparison"]["all_match"] is True, (
            "Dataset-level statistics differ between runs: "
            + str({
                k: v for k, v in repro_result["statistics_comparison"]["details"].items()
                if not v["match"]
            })
        )

    def test_salary_mean_matches(self, repro_result):
        sal = repro_result["statistics_comparison"]["details"].get("salary_mean")
        assert sal is not None, "salary_mean not in statistics comparison"
        assert sal["match"] is True, (
            f"Salary mean differs: run1={sal['run_1']}, run2={sal['run_2']}"
        )

    def test_attrition_rate_matches(self, repro_result):
        rate = repro_result["statistics_comparison"]["details"].get(
            "voluntary_attrition_rate"
        )
        assert rate is not None, "voluntary_attrition_rate not in statistics"
        assert rate["match"] is True

    def test_sentiment_mean_matches(self, repro_result):
        sent = repro_result["statistics_comparison"]["details"].get("sentiment_mean")
        assert sent is not None, "sentiment_mean not in statistics comparison"
        assert sent["match"] is True

    def test_salary_std_matches(self, repro_result):
        std = repro_result["statistics_comparison"]["details"].get("salary_std")
        assert std is not None, "salary_std not in statistics comparison"
        assert std["match"] is True
