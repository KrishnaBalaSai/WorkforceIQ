"""
In-memory Validation Engine for WorkforceIQ Synthetic Data Generation.
Verifies primary keys, foreign key referential integrity, ENUM validity,
date logic, and duplicate records.
"""

from typing import Dict, List, Any, Tuple
import datetime

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
}

def validate_dataset(datasets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Performs comprehensive structural and relational validation of generated datasets.
    Returns a dictionary with summary statistics and any validation errors.
    """
    errors: List[str] = []
    warnings: List[str] = []
    stats: Dict[str, int] = {}
    
    # 1. Row counts
    for tbl_name, rows in datasets.items():
        stats[tbl_name] = len(rows)
        if len(rows) == 0 and tbl_name not in ("data_anomalies",):
            errors.append(f"Table {tbl_name} is unexpectedly empty.")

    # 2. Extract Primary Key Sets for Referential Checks
    dept_ids = {r["department_id"] for r in datasets.get("departments", [])}
    role_ids = {r["role_id"] for r in datasets.get("job_roles", [])}
    skill_ids = {r["skill_id"] for r in datasets.get("skills", [])}
    emp_ids = {r["employee_id"] for r in datasets.get("employees", [])}
    proj_ids = {r["project_id"] for r in datasets.get("projects", [])}
    risk_score_ids = {r["score_id"] for r in datasets.get("attrition_risk_scores", [])}

    # Check PK uniqueness in employees
    if len(emp_ids) != len(datasets.get("employees", [])):
        errors.append(f"Duplicate employee_id detected in employees table! ({len(emp_ids)} unique vs {len(datasets['employees'])} total)")
        
    # Check email uniqueness in employees
    emails = [r["email"] for r in datasets.get("employees", [])]
    if len(emails) != len(set(emails)):
        errors.append(f"Duplicate email detected in employees table! ({len(set(emails))} unique vs {len(emails)} total)")

    # 3. Foreign Key Checks
    # employees
    for emp in datasets.get("employees", []):
        if emp["department_id"] not in dept_ids:
            errors.append(f"Employee {emp['employee_id']} references unknown department {emp['department_id']}")
        if emp["role_id"] not in role_ids:
            errors.append(f"Employee {emp['employee_id']} references unknown role {emp['role_id']}")
        if emp["manager_id"] is not None and emp["manager_id"] not in emp_ids:
            errors.append(f"Employee {emp['employee_id']} references unknown manager {emp['manager_id']}")
        if emp["status"] not in VALID_ENUMS["employment_status_enum"]:
            errors.append(f"Invalid status enum {emp['status']} on employee {emp['employee_id']}")

    # employee_skills
    for es in datasets.get("employee_skills", []):
        if es["employee_id"] not in emp_ids:
            errors.append(f"employee_skills references unknown employee {es['employee_id']}")
        if es["skill_id"] not in skill_ids:
            errors.append(f"employee_skills references unknown skill {es['skill_id']}")

    # compensation_records
    for comp in datasets.get("compensation_records", []):
        if comp["employee_id"] not in emp_ids:
            errors.append(f"compensation_records references unknown employee {comp['employee_id']}")
        if comp["effective_to"] is not None and comp["effective_to"] < comp["effective_from"]:
            errors.append(f"compensation_records {comp['compensation_id']} has effective_to < effective_from")
        if comp["base_salary"] <= 0:
            errors.append(f"compensation_records {comp['compensation_id']} has non-positive salary")

    # performance_evaluations
    for pe in datasets.get("performance_evaluations", []):
        if pe["employee_id"] not in emp_ids:
            errors.append(f"performance_evaluations references unknown employee {pe['employee_id']}")
        if pe["reviewer_id"] not in emp_ids:
            errors.append(f"performance_evaluations references unknown reviewer {pe['reviewer_id']}")
        if pe["rating"] not in VALID_ENUMS["review_rating_enum"]:
            errors.append(f"Invalid review rating {pe['rating']} on evaluation {pe['evaluation_id']}")

    # engagement_surveys
    for es in datasets.get("engagement_surveys", []):
        if es["employee_id"] not in emp_ids:
            errors.append(f"engagement_surveys references unknown employee {es['employee_id']}")
        if not (1 <= es["job_satisfaction"] <= 5):
            errors.append(f"Invalid job_satisfaction score on survey {es['survey_id']}")

    # project_assignments
    for pa in datasets.get("project_assignments", []):
        if pa["employee_id"] not in emp_ids:
            errors.append(f"project_assignments references unknown employee {pa['employee_id']}")
        if pa["project_id"] not in proj_ids:
            errors.append(f"project_assignments references unknown project {pa['project_id']}")
        if pa["end_date"] is not None and pa["end_date"] < pa["start_date"]:
            errors.append(f"project_assignments {pa['assignment_id']} has end_date < start_date")

    # exit_records
    for ex in datasets.get("exit_records", []):
        if ex["employee_id"] not in emp_ids:
            errors.append(f"exit_records references unknown employee {ex['employee_id']}")
        if ex["separation_type"] not in VALID_ENUMS["separation_type_enum"]:
            errors.append(f"Invalid separation_type {ex['separation_type']} on exit {ex['exit_id']}")
        if ex["regret_status"] not in VALID_ENUMS["regret_status_enum"]:
            errors.append(f"Invalid regret_status {ex['regret_status']} on exit {ex['exit_id']}")

    # Check voluntary attrition rate within target 5% - 15% bounds
    total_emps = len(emp_ids)
    vol_exits = len([ex for ex in datasets.get("exit_records", []) if ex["separation_type"] == "VOLUNTARY"])
    vol_attrition_pct = (vol_exits / total_emps * 100.0) if total_emps > 0 else 0.0
    
    stats["total_employees"] = total_emps
    stats["voluntary_exits"] = vol_exits
    stats["voluntary_attrition_rate_pct"] = round(vol_attrition_pct, 2)
    
    if not (5.0 <= vol_attrition_pct <= 15.0):
        warnings.append(
            f"Voluntary attrition rate is {vol_attrition_pct:.2f}%, outside the 5.0% - 15.0% target band."
        )

    return {
        "is_valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "statistics": stats,
    }
