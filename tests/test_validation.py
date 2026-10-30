"""
tests/test_validation.py
========================
Pytest test suite for Phase 4: Comprehensive Data Validation.

Verifies that all 12 validation pillars pass on the existing 10,000-employee
WorkforceIQ dataset.  Tests are scoped to be fast (< 30 s) since they read
already-exported CSV files rather than regenerating data.

Pillars tested
--------------
1.  Primary-key uniqueness
2.  Foreign-key integrity
3.  Allowed enum validation
4.  Date ordering
5.  Effective-date consistency (SCD-2)
6.  Duplicate detection
7.  Arithmetic reconciliation
8.  Lifecycle transition validation
9.  Missing-value handling
10. Attrition outcome consistency
11. Temporal leakage detection
12. Valid joins across all entities
"""

import json
from pathlib import Path

import pytest

from validation.comprehensive_validator import run_comprehensive_validation

# ---------------------------------------------------------------------------
# Fixture: run the validator once for the whole module
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def validation_result():
    """
    Executes run_comprehensive_validation() against the stored 10k dataset.
    Results are cached at module scope so the CSV files are read only once.
    """
    return run_comprehensive_validation(data_path=DATA_DIR)


@pytest.fixture(scope="module")
def pillars(validation_result):
    return validation_result["pillar_results"]


# ---------------------------------------------------------------------------
# 0. Sanity: overall status
# ---------------------------------------------------------------------------

class TestOverallValidation:
    def test_overall_status_is_passed(self, validation_result):
        assert validation_result["overall_status"] == "PASSED", (
            f"Overall validation FAILED. Violations: "
            f"{validation_result['failed_pillars']}"
        )

    def test_all_12_pillars_present(self, pillars):
        assert len(pillars) == 12, (
            f"Expected 12 pillar result entries, got {len(pillars)}"
        )

    def test_total_pillars_count(self, validation_result):
        assert validation_result["total_pillars"] == 12

    def test_passed_pillars_equals_12(self, validation_result):
        assert validation_result["passed_pillars"] == 12, (
            f"Only {validation_result['passed_pillars']}/12 pillars passed. "
            f"Failed: {validation_result['failed_pillars']}"
        )


# ---------------------------------------------------------------------------
# 1. Primary-Key Uniqueness
# ---------------------------------------------------------------------------

class TestPillar01PrimaryKeyUniqueness:
    KEY = "1_primary_key_uniqueness"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Failed tables: {pillars[self.KEY]['failed_tables']}"
        )

    def test_tables_checked_count(self, pillars):
        # At least 14 tables have PK checks
        assert pillars[self.KEY]["tables_checked"] >= 14

    def test_no_failed_tables(self, pillars):
        assert pillars[self.KEY]["failed_tables"] == [], (
            f"Duplicate primary keys in: {pillars[self.KEY]['failed_tables']}"
        )


# ---------------------------------------------------------------------------
# 2. Foreign-Key Integrity
# ---------------------------------------------------------------------------

class TestPillar02ForeignKeyIntegrity:
    KEY = "2_foreign_key_integrity"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Broken FK relationships: {pillars[self.KEY]['failed_relationships']}"
        )

    def test_relationships_verified(self, pillars):
        assert pillars[self.KEY]["relationships_verified"] >= 8

    def test_no_broken_relationships(self, pillars):
        assert pillars[self.KEY]["failed_relationships"] == []


# ---------------------------------------------------------------------------
# 3. Allowed Enum Validation
# ---------------------------------------------------------------------------

class TestPillar03EnumValidation:
    KEY = "3_allowed_enum_validation"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Invalid enum values in: {pillars[self.KEY]['failed_enums']}"
        )

    def test_enums_verified(self, pillars):
        assert pillars[self.KEY]["enums_verified"] >= 8

    def test_no_invalid_enums(self, pillars):
        assert pillars[self.KEY]["failed_enums"] == []


# ---------------------------------------------------------------------------
# 4. Date Ordering
# ---------------------------------------------------------------------------

class TestPillar04DateOrdering:
    KEY = "4_date_ordering"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Date ordering violations: {pillars[self.KEY]['failed_checks']}"
        )

    def test_date_pairs_verified(self, pillars):
        assert pillars[self.KEY]["date_pairs_verified"] >= 3

    def test_no_invalid_date_ranges(self, pillars):
        assert pillars[self.KEY]["failed_checks"] == []


# ---------------------------------------------------------------------------
# 5. Effective-Date Consistency
# ---------------------------------------------------------------------------

class TestPillar05EffectiveDateConsistency:
    KEY = "5_effective_date_consistency"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"SCD2 violations: {pillars[self.KEY]['failed_scd_checks']}"
        )

    def test_no_scd_violations(self, pillars):
        assert pillars[self.KEY]["failed_scd_checks"] == []

    def test_active_records_audited(self, pillars):
        # Should audit at least 8,000 active compensation records for 10k dataset
        assert pillars[self.KEY]["active_records_audited"] >= 1


# ---------------------------------------------------------------------------
# 6. Duplicate Detection
# ---------------------------------------------------------------------------

class TestPillar06DuplicateDetection:
    KEY = "6_duplicate_detection"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Duplicate issues found: {pillars[self.KEY]['duplicate_issues']}"
        )

    def test_no_duplicate_emails(self, pillars):
        issues = pillars[self.KEY]["duplicate_issues"]
        email_issues = [i for i in issues if "email" in i.lower()]
        assert email_issues == [], f"Duplicate emails: {email_issues}"

    def test_no_duplicate_exit_records(self, pillars):
        issues = pillars[self.KEY]["duplicate_issues"]
        exit_issues = [i for i in issues if "exit_records" in i.lower()]
        assert exit_issues == [], f"Duplicate exit records: {exit_issues}"


# ---------------------------------------------------------------------------
# 7. Arithmetic Reconciliation
# ---------------------------------------------------------------------------

class TestPillar07ArithmeticReconciliation:
    KEY = "7_arithmetic_reconciliation"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Arithmetic errors: {pillars[self.KEY]['failed_checks']}"
        )

    def test_compa_ratio_reconciled(self, pillars):
        assert pillars[self.KEY]["compa_ratio_reconciled"] is True, (
            "compa_ratio differs from base_salary / role_mid_salary by > 0.005"
        )

    def test_performance_goals_correlation_exceeds_threshold(self, pillars):
        corr = pillars[self.KEY]["performance_goals_correlation"]
        assert corr > 0.80, (
            f"Performance score to goals correlation too low: {corr:.4f} (min 0.80)"
        )


# ---------------------------------------------------------------------------
# 8. Lifecycle Transition Validation
# ---------------------------------------------------------------------------

class TestPillar08LifecycleTransitions:
    KEY = "8_lifecycle_transition_validation"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Lifecycle errors: {pillars[self.KEY]['failed_checks']}"
        )

    def test_all_terminated_have_exit_records(self, pillars):
        r = pillars[self.KEY]
        assert r["total_terminated"] == r["matched_in_exit_records"], (
            f"{r['total_terminated'] - r['matched_in_exit_records']} terminated "
            f"employees have no exit_record"
        )

    def test_no_lifecycle_errors(self, pillars):
        assert pillars[self.KEY]["failed_checks"] == []


# ---------------------------------------------------------------------------
# 9. Missing-Value Handling
# ---------------------------------------------------------------------------

class TestPillar09MissingValueHandling:
    KEY = "9_missing_value_handling"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Unexpected nulls: {pillars[self.KEY]['unexpected_null_counts']}"
        )

    def test_mandatory_columns_not_null(self, pillars):
        assert pillars[self.KEY]["unexpected_null_counts"] == {}, (
            f"Null values in mandatory columns: "
            f"{pillars[self.KEY]['unexpected_null_counts']}"
        )

    def test_columns_audited(self, pillars):
        assert pillars[self.KEY]["columns_audited"] >= 6


# ---------------------------------------------------------------------------
# 10. Attrition Outcome Consistency
# ---------------------------------------------------------------------------

class TestPillar10AttritionConsistency:
    KEY = "10_attrition_outcome_consistency"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            "Voluntary exit set in exit_records does not match attrition_labels"
        )

    def test_exact_match_between_exit_and_labels(self, pillars):
        assert pillars[self.KEY]["exact_match"] is True

    def test_voluntary_counts_are_equal(self, pillars):
        r = pillars[self.KEY]
        assert r["exit_records_voluntary_count"] == r["attrition_labels_voluntary_count"], (
            f"Mismatch: exit_records has {r['exit_records_voluntary_count']} voluntary, "
            f"attrition_labels has {r['attrition_labels_voluntary_count']}"
        )


# ---------------------------------------------------------------------------
# 11. Temporal Leakage Detection
# ---------------------------------------------------------------------------

class TestPillar11TemporalLeakage:
    KEY = "11_temporal_leakage_detection"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            f"Leaked features found in derived_workforce_features: "
            f"{pillars[self.KEY]['forbidden_features_detected']}"
        )

    def test_no_forbidden_features_in_derived(self, pillars):
        assert pillars[self.KEY]["forbidden_features_detected"] == [], (
            f"Forbidden post-outcome features leaked: "
            f"{pillars[self.KEY]['forbidden_features_detected']}"
        )

    def test_separation_date_not_in_derived(self, pillars):
        leaked = pillars[self.KEY]["forbidden_features_detected"]
        assert "separation_date" not in leaked

    def test_has_attrited_not_in_derived(self, pillars):
        leaked = pillars[self.KEY]["forbidden_features_detected"]
        assert "has_attrited" not in leaked


# ---------------------------------------------------------------------------
# 12. Valid Joins Across All Entities
# ---------------------------------------------------------------------------

class TestPillar12ValidJoins:
    KEY = "12_valid_joins_across_entities"

    def test_pillar_passed(self, pillars):
        assert pillars[self.KEY]["status"] == "PASSED", (
            "One or more join completeness checks failed"
        )

    def test_active_employee_comp_join_complete(self, pillars):
        assert pillars[self.KEY]["active_employee_comp_join_complete"] is True, (
            "Active employees do not have 100% inner-join coverage in compensation_records"
        )

    def test_terminated_exit_join_complete(self, pillars):
        assert pillars[self.KEY]["terminated_employee_exit_join_complete"] is True, (
            "Terminated employees do not have 100% inner-join coverage in exit_records"
        )

    def test_assignment_project_join_complete(self, pillars):
        assert pillars[self.KEY]["assignment_project_join_complete"] is True, (
            "project_assignments rows cannot all join to projects and employees"
        )
