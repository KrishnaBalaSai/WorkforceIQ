"""
WorkforceIQ Comprehensive Enterprise Data Validator (Phase 4).
Implements the 12 validation pillars:
1. Primary-key uniqueness.
2. Foreign-key integrity.
3. Allowed enum validation.
4. Date ordering.
5. Effective-date consistency.
6. Duplicate detection.
7. Arithmetic reconciliation.
8. Lifecycle transition validation.
9. Missing-value handling.
10. Attrition outcome consistency.
11. Temporal leakage detection.
12. Valid joins across all entities.
"""

from pathlib import Path
from typing import Dict, List, Any, Tuple
import hashlib
import json
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_ENUMS = {
    "employment_status_enum": {'APPLICANT', 'ONBOARDING', 'ACTIVE', 'ON_LEAVE', 'NOTICE_PERIOD', 'TERMINATED', 'RETIRED'},
    "employment_type_enum": {'FULL_TIME', 'PART_TIME', 'CONTRACTOR', 'INTERN'},
    "work_location_enum": {'ONSITE', 'HYBRID', 'REMOTE'},
    "separation_type_enum": {'VOLUNTARY', 'INVOLUNTARY', 'RETIREMENT', 'CONTRACT_END'},
    "regret_status_enum": {'REGRETTABLE', 'NON_REGRETTABLE', 'UNDETERMINED'},
    "risk_tier_enum": {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'},
    "intervention_type_enum": {
        'COMPENSATION_INCREASE', 'RETENTION_BONUS', 'ROLE_PROMOTION',
        'PROJECT_REASSIGNMENT', 'FLEXIBLE_WORK_SCHEDULE', 'EXECUTIVE_MENTORSHIP', 'CAREER_DEVELOPMENT'
    },
    "intervention_status_enum": {
        'RECOMMENDED', 'APPROVED', 'REJECTED', 'OFFERED', 'ACCEPTED', 'DECLINED', 'COMPLETED', 'FAILED'
    },
    "review_rating_enum": {
        'UNSATISFACTORY', 'NEEDS_IMPROVEMENT', 'MEETS_EXPECTATIONS', 'EXCEEDS_EXPECTATIONS', 'OUTSTANDING'
    },
    "leave_type_enum": {'ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'BEREAVEMENT', 'UNPAID'},
    "anomaly_type_enum": {
        'POST_TERMINATION_ACTIVITY', 'CIRCULAR_HIERARCHY', 'COMPENSATION_INVERSION',
        'LEAVE_HOUR_CONFLICT', 'SCHEMA_VIOLATION', 'DATA_LEAKAGE'
    },
    "severity_level_enum": {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'},
}

def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def run_comprehensive_validation(data_path: Path = None) -> Dict[str, Any]:
    """
    Executes full 12-pillar validation on the stored datasets.
    """
    if data_path is None:
        data_path = DATA_DIR

    gen_dir = data_path / "generated"
    gt_dir = data_path / "ground_truth"

    # Load all tables
    depts = pd.read_csv(gen_dir / "departments.csv")
    roles = pd.read_csv(gen_dir / "job_roles.csv")
    skills = pd.read_csv(gen_dir / "skills.csv")
    emps = pd.read_csv(gen_dir / "employees.csv")
    emp_skills = pd.read_csv(gen_dir / "employee_skills.csv")
    history = pd.read_csv(gen_dir / "employee_history.csv")
    comps = pd.read_csv(gen_dir / "compensation_records.csv")
    reviews = pd.read_csv(gen_dir / "performance_evaluations.csv")
    surveys = pd.read_csv(gen_dir / "engagement_surveys.csv")
    projects = pd.read_csv(gen_dir / "projects.csv")
    assignments = pd.read_csv(gen_dir / "project_assignments.csv")
    time_off = pd.read_csv(gen_dir / "time_off_records.csv")
    risk_scores = pd.read_csv(gen_dir / "attrition_risk_scores.csv")
    interventions = pd.read_csv(gen_dir / "retention_interventions.csv")
    anomalies = pd.read_csv(gen_dir / "data_anomalies.csv")
    derived = pd.read_csv(gen_dir / "derived_workforce_features.csv")
    
    exits = pd.read_csv(gt_dir / "exit_records.csv")
    labels = pd.read_csv(gt_dir / "attrition_labels.csv")
    manifest = pd.read_csv(gt_dir / "anomaly_manifest.csv")

    pillar_results: Dict[str, Any] = {}
    total_violations = 0

    # -------------------------------------------------------------------------
    # 1. Primary-Key Uniqueness
    # -------------------------------------------------------------------------
    pk_checks = {
        "departments": ("department_id", depts["department_id"].nunique() == len(depts)),
        "job_roles": ("role_id", roles["role_id"].nunique() == len(roles)),
        "skills": ("skill_id", skills["skill_id"].nunique() == len(skills)),
        "employees": ("employee_id", emps["employee_id"].nunique() == len(emps)),
        "compensation_records": ("compensation_id", comps["compensation_id"].nunique() == len(comps)),
        "performance_evaluations": ("evaluation_id", reviews["evaluation_id"].nunique() == len(reviews)),
        "engagement_surveys": ("survey_id", surveys["survey_id"].nunique() == len(surveys)),
        "projects": ("project_id", projects["project_id"].nunique() == len(projects)),
        "project_assignments": ("assignment_id", assignments["assignment_id"].nunique() == len(assignments)),
        "time_off_records": ("leave_id", time_off["leave_id"].nunique() == len(time_off)),
        "attrition_risk_scores": ("score_id", risk_scores["score_id"].nunique() == len(risk_scores)),
        "retention_interventions": ("intervention_id", interventions["intervention_id"].nunique() == len(interventions)),
        "exit_records": ("exit_id", exits["exit_id"].nunique() == len(exits)),
        "data_anomalies": ("anomaly_id", anomalies["anomaly_id"].nunique() == len(anomalies)),
    }
    pk_failed = [tbl for tbl, (_, valid) in pk_checks.items() if not valid]
    pillar_results["1_primary_key_uniqueness"] = {
        "status": "PASSED" if not pk_failed else "FAILED",
        "tables_checked": len(pk_checks),
        "failed_tables": pk_failed,
    }
    total_violations += len(pk_failed)

    # -------------------------------------------------------------------------
    # 2. Foreign-Key Integrity
    # -------------------------------------------------------------------------
    emp_ids = set(emps["employee_id"])
    dept_ids = set(depts["department_id"])
    role_ids = set(roles["role_id"])
    skill_ids = set(skills["skill_id"])
    proj_ids = set(projects["project_id"])

    fk_errors = []
    if not emps["department_id"].isin(dept_ids).all():
        fk_errors.append("employees -> departments")
    if not emps["role_id"].isin(role_ids).all():
        fk_errors.append("employees -> job_roles")
    if not comps["employee_id"].isin(emp_ids).all():
        fk_errors.append("compensation_records -> employees")
    if not reviews["employee_id"].isin(emp_ids).all():
        fk_errors.append("performance_evaluations -> employees")
    if not surveys["employee_id"].isin(emp_ids).all():
        fk_errors.append("engagement_surveys -> employees")
    if not assignments["employee_id"].isin(emp_ids).all():
        fk_errors.append("project_assignments -> employees")
    if not assignments["project_id"].isin(proj_ids).all():
        fk_errors.append("project_assignments -> projects")
    if not exits["employee_id"].isin(emp_ids).all():
        fk_errors.append("exit_records -> employees")

    pillar_results["2_foreign_key_integrity"] = {
        "status": "PASSED" if not fk_errors else "FAILED",
        "relationships_verified": 8,
        "failed_relationships": fk_errors,
    }
    total_violations += len(fk_errors)

    # -------------------------------------------------------------------------
    # 3. Allowed Enum Validation
    # -------------------------------------------------------------------------
    enum_errors = []
    if not set(emps["status"]).issubset(VALID_ENUMS["employment_status_enum"]):
        enum_errors.append("employees.status")
    if not set(emps["employment_type"]).issubset(VALID_ENUMS["employment_type_enum"]):
        enum_errors.append("employees.employment_type")
    if not set(emps["work_location"]).issubset(VALID_ENUMS["work_location_enum"]):
        enum_errors.append("employees.work_location")
    if not set(exits["separation_type"]).issubset(VALID_ENUMS["separation_type_enum"]):
        enum_errors.append("exit_records.separation_type")
    if not set(exits["regret_status"]).issubset(VALID_ENUMS["regret_status_enum"]):
        enum_errors.append("exit_records.regret_status")
    if not set(risk_scores["risk_tier"]).issubset(VALID_ENUMS["risk_tier_enum"]):
        enum_errors.append("attrition_risk_scores.risk_tier")
    if not set(interventions["intervention_type"]).issubset(VALID_ENUMS["intervention_type_enum"]):
        enum_errors.append("retention_interventions.intervention_type")
    if not set(reviews["rating"]).issubset(VALID_ENUMS["review_rating_enum"]):
        enum_errors.append("performance_evaluations.rating")

    pillar_results["3_allowed_enum_validation"] = {
        "status": "PASSED" if not enum_errors else "FAILED",
        "enums_verified": 8,
        "failed_enums": enum_errors,
    }
    total_violations += len(enum_errors)

    # -------------------------------------------------------------------------
    # 4. Date Ordering
    # -------------------------------------------------------------------------
    date_ordering_errors = []
    # hire_date <= separation_date
    exit_emp_merge = exits.merge(emps[["employee_id", "hire_date"]], on="employee_id")
    if (exit_emp_merge["separation_date"] < exit_emp_merge["hire_date"]).any():
        date_ordering_errors.append("exit_records.separation_date < employees.hire_date")
    # project_assignments start_date <= end_date
    non_null_assign_dates = assignments[assignments["end_date"].notnull()]
    if (non_null_assign_dates["end_date"] < non_null_assign_dates["start_date"]).any():
        date_ordering_errors.append("project_assignments.end_date < start_date")
    # time_off start_date <= end_date
    if (time_off["end_date"] < time_off["start_date"]).any():
        date_ordering_errors.append("time_off_records.end_date < start_date")

    pillar_results["4_date_ordering"] = {
        "status": "PASSED" if not date_ordering_errors else "FAILED",
        "date_pairs_verified": 3,
        "failed_checks": date_ordering_errors,
    }
    total_violations += len(date_ordering_errors)

    # -------------------------------------------------------------------------
    # 5. Effective-Date Consistency (SCD Type 2)
    # -------------------------------------------------------------------------
    scd_errors = []
    # Single active current record for active employees
    active_emps = emps[emps["is_active"] == True]["employee_id"]
    active_comps = comps[comps["is_current"] == True]
    comp_active_counts = active_comps[active_comps["employee_id"].isin(active_emps)].groupby("employee_id").size()
    if (comp_active_counts != 1).any():
        scd_errors.append("Active employee possesses != 1 current compensation record")
    # effective_to >= effective_from
    closed_comps = comps[comps["effective_to"].notnull()]
    if (closed_comps["effective_to"] < closed_comps["effective_from"]).any():
        scd_errors.append("compensation_records effective_to < effective_from")

    pillar_results["5_effective_date_consistency"] = {
        "status": "PASSED" if not scd_errors else "FAILED",
        "active_records_audited": len(active_comps),
        "failed_scd_checks": scd_errors,
    }
    total_violations += len(scd_errors)

    # -------------------------------------------------------------------------
    # 6. Duplicate Detection
    # -------------------------------------------------------------------------
    dup_errors = []
    if emps["email"].duplicated().any():
        dup_errors.append(f"{emps['email'].duplicated().sum()} duplicate corporate emails in employees")
    if emp_skills.duplicated(subset=["employee_id", "skill_id"]).any():
        dup_errors.append("Duplicate (employee_id, skill_id) in employee_skills")
    if exits["employee_id"].duplicated().any():
        dup_errors.append("Duplicate employee_id in exit_records (violates 1:1 constraint)")

    pillar_results["6_duplicate_detection"] = {
        "status": "PASSED" if not dup_errors else "FAILED",
        "duplicate_issues": dup_errors,
    }
    total_violations += len(dup_errors)

    # -------------------------------------------------------------------------
    # 7. Arithmetic Reconciliation
    # -------------------------------------------------------------------------
    # A. Verify derived compa_ratio formula: base_salary / role_midpoint
    role_mid_map = dict(zip(roles["role_id"], roles["mid_salary"]))
    derived["expected_compa"] = (derived["base_salary"] / derived["role_id"].map(role_mid_map)).round(3)
    compa_diff = (derived["compa_ratio"] - derived["expected_compa"]).abs()
    compa_reconciled = (compa_diff <= 0.005).all()

    # B. Performance evaluation numeric_score (1.00-5.00) vs goals_met (0-150%) correlation
    perf_corr = reviews["numeric_score"].corr(reviews["goals_met_pct"])
    perf_reconciled = perf_corr > 0.80

    arithmetic_errors = []
    if not compa_reconciled:
        arithmetic_errors.append("Compa-ratio arithmetic deviation > 0.005")
    if not perf_reconciled:
        arithmetic_errors.append("Performance score to goals achievement correlation < 0.80")

    pillar_results["7_arithmetic_reconciliation"] = {
        "status": "PASSED" if not arithmetic_errors else "FAILED",
        "compa_ratio_reconciled": bool(compa_reconciled),
        "performance_goals_correlation": round(float(perf_corr), 4),
        "failed_checks": arithmetic_errors,
    }
    total_violations += len(arithmetic_errors)

    # -------------------------------------------------------------------------
    # 8. Lifecycle Transition Validation
    # -------------------------------------------------------------------------
    # Rule: Employees with status = TERMINATED must have is_active = False and exit record
    term_emps = set(emps[emps["status"] == "TERMINATED"]["employee_id"])
    exit_emp_ids = set(exits["employee_id"])
    term_diff = term_emps - exit_emp_ids

    lifecycle_errors = []
    if term_diff:
        lifecycle_errors.append(f"{len(term_diff)} terminated employees missing exit_records")

    pillar_results["8_lifecycle_transition_validation"] = {
        "status": "PASSED" if not lifecycle_errors else "FAILED",
        "total_terminated": len(term_emps),
        "matched_in_exit_records": len(term_emps & exit_emp_ids),
        "failed_checks": lifecycle_errors,
    }
    total_violations += len(lifecycle_errors)

    # -------------------------------------------------------------------------
    # 9. Missing-Value Handling
    # -------------------------------------------------------------------------
    # Mandatory non-null columns
    non_null_audit = {
        "employees.email": emps["email"].isnull().sum(),
        "employees.hire_date": emps["hire_date"].isnull().sum(),
        "job_roles.min_salary": roles["min_salary"].isnull().sum(),
        "compensation_records.base_salary": comps["base_salary"].isnull().sum(),
        "performance_evaluations.numeric_score": reviews["numeric_score"].isnull().sum(),
        "attrition_risk_scores.flight_risk_prob": risk_scores["flight_risk_prob"].isnull().sum(),
    }
    unexpected_nulls = {col: cnt for col, cnt in non_null_audit.items() if cnt > 0}

    pillar_results["9_missing_value_handling"] = {
        "status": "PASSED" if not unexpected_nulls else "FAILED",
        "columns_audited": len(non_null_audit),
        "unexpected_null_counts": unexpected_nulls,
    }
    total_violations += len(unexpected_nulls)

    # -------------------------------------------------------------------------
    # 10. Attrition Outcome Consistency
    # -------------------------------------------------------------------------
    # Cross-reference exit_records with attrition_labels
    vol_exit_set = set(exits[exits["separation_type"] == "VOLUNTARY"]["employee_id"])
    vol_label_set = set(labels[labels["has_attrited_voluntary"] == True]["employee_id"])
    attrition_outcome_match = (vol_exit_set == vol_label_set)

    pillar_results["10_attrition_outcome_consistency"] = {
        "status": "PASSED" if attrition_outcome_match else "FAILED",
        "exit_records_voluntary_count": len(vol_exit_set),
        "attrition_labels_voluntary_count": len(vol_label_set),
        "exact_match": bool(attrition_outcome_match),
    }
    if not attrition_outcome_match:
        total_violations += 1

    # -------------------------------------------------------------------------
    # 11. Temporal Leakage Detection
    # -------------------------------------------------------------------------
    forbidden_features = {"separation_date", "has_attrited", "separation_type", "exit_id"}
    leaked_cols = forbidden_features.intersection(set(derived.columns))

    pillar_results["11_temporal_leakage_detection"] = {
        "status": "PASSED" if not leaked_cols else "FAILED",
        "forbidden_features_detected": list(leaked_cols),
        "clean_derived_columns": len(derived.columns),
    }
    total_violations += len(leaked_cols)

    # -------------------------------------------------------------------------
    # 12. Valid Joins Across All Entities
    # -------------------------------------------------------------------------
    # A. Full graph left join from employees to departments, roles, and current compensation
    j1 = emps.merge(depts, on="department_id", how="inner")
    j2 = j1.merge(roles, on="role_id", how="inner")
    curr_c = comps[comps["is_current"] == True]
    j_active = emps[emps["is_active"] == True].merge(curr_c, on="employee_id", how="inner")
    active_join_complete = (len(j_active) == len(emps[emps["is_active"] == True]))

    # B. Terminated employees join 100% to exit_records
    term_emps_df = emps[emps["status"] == "TERMINATED"]
    j_exit = term_emps_df.merge(exits, on="employee_id", how="inner")
    exit_join_complete = (len(j_exit) == len(term_emps_df))

    # C. Project assignments join 100% to projects and employees
    j_assign = assignments.merge(projects, on="project_id", how="inner").merge(emps, on="employee_id", how="inner")
    assign_join_complete = (len(j_assign) == len(assignments))

    join_complete = active_join_complete and exit_join_complete and assign_join_complete

    pillar_results["12_valid_joins_across_entities"] = {
        "status": "PASSED" if join_complete else "FAILED",
        "active_employee_comp_join_complete": bool(active_join_complete),
        "terminated_employee_exit_join_complete": bool(exit_join_complete),
        "assignment_project_join_complete": bool(assign_join_complete),
        "active_joined_count": len(j_active),
        "exit_joined_count": len(j_exit),
    }
    if not join_complete:
        total_violations += 1

    # Overall Summary
    overall_status = "PASSED" if total_violations == 0 else "FAILED"
    
    summary = {
        "overall_status": overall_status,
        "total_pillars": 12,
        "passed_pillars": 12 - total_violations,
        "failed_pillars": total_violations,
        "pillar_results": pillar_results,
    }

    return summary

def generate_source_manifest(data_path: Path = None) -> Dict[str, Any]:
    """
    Computes file sizes and SHA-256 hashes for all existing datasets.
    """
    if data_path is None:
        data_path = DATA_DIR

    file_manifest = {}
    for p in sorted(data_path.rglob("*")):
        if p.is_file() and p.suffix in (".csv", ".json") and "manifest" not in p.name:
            rel = p.relative_to(data_path).as_posix()
            file_manifest[rel] = {
                "size_bytes": p.stat().st_size,
                "sha256": compute_file_sha256(p),
            }

    return {
        "dataset_root": str(data_path),
        "total_files": len(file_manifest),
        "files": file_manifest,
    }

if __name__ == "__main__":
    print("Running 12-pillar comprehensive validation...")
    res = run_comprehensive_validation()
    print(f"Overall Status: {res['overall_status']}")
    print(f"Passed Pillars: {res['passed_pillars']} / {res['total_pillars']}")
    for k, v in res["pillar_results"].items():
        print(f"  [{v['status']}] {k}")
