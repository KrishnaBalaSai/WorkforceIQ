"""
Pytest suite for Phase 1 Database Schema and Architecture Verification
Audits all 8 checklist requirements:
1. All 10 mandatory entities exist.
2. Every entity has a primary key.
3. Foreign keys and relationships are correct.
4. Cardinalities and unique constraints are enforced.
5. Effective dates and lifecycle states are defined.
6. All fields are documented in the data dictionary.
7. The four mandatory anomaly scenarios are covered.
8. Temporal integrity and historical event tracking are addressed.
"""

import re
from pathlib import Path
import pytest

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
DATA_DICT_FILE = Path(__file__).resolve().parent.parent / "docs" / "data_dictionary.md"

MANDATORY_ENTITIES = [
    "departments",
    "job_roles",
    "employees",
    "compensation_records",
    "performance_evaluations",
    "engagement_surveys",
    "projects",
    "project_assignments",
    "attrition_risk_scores",
    "retention_interventions",
    "exit_records",
]

SUPPORTING_TABLES = [
    "skills",
    "employee_skills",
    "employee_history",
    "time_off_records",
    "data_anomalies",
    "audit_logs",
]

ALL_TABLES = MANDATORY_ENTITIES + SUPPORTING_TABLES

MANDATORY_ENUMS = [
    "employment_status_enum",
    "employment_type_enum",
    "work_location_enum",
    "separation_type_enum",
    "regret_status_enum",
    "risk_tier_enum",
    "intervention_type_enum",
    "intervention_status_enum",
    "review_rating_enum",
    "anomaly_type_enum",
    "severity_level_enum",
    "leave_type_enum",
]

ANOMALY_VIEWS = [
    "v_anomaly_post_termination_activity",
    "v_anomaly_circular_hierarchy",
    "v_anomaly_salary_band_breach",
    "v_anomaly_leave_hour_conflict",
]

ANALYTICAL_VIEWS = [
    "v_employee_360",
    "v_high_risk_retention_watchlist",
]

@pytest.fixture(scope="module")
def schema_sql():
    assert SCHEMA_FILE.exists(), f"Schema file not found at {SCHEMA_FILE}"
    return SCHEMA_FILE.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def data_dict():
    assert DATA_DICT_FILE.exists(), f"Data dictionary not found at {DATA_DICT_FILE}"
    return DATA_DICT_FILE.read_text(encoding="utf-8")

# 1. All 10 mandatory entities exist
def test_1_mandatory_entities_exist(schema_sql):
    for table_name in MANDATORY_ENTITIES:
        pattern = rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\("
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing core table: {table_name}"
    for table_name in SUPPORTING_TABLES:
        pattern = rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\("
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing supporting table: {table_name}"

# 2. Every entity has a primary key
def test_2_every_entity_has_primary_key(schema_sql):
    for table_name in ALL_TABLES:
        table_match = re.search(
            rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\((.*?)\);",
            schema_sql,
            re.DOTALL | re.IGNORECASE
        )
        assert table_match, f"Could not find table definition for: {table_name}"
        table_body = table_match.group(1)
        assert "PRIMARY KEY" in table_body.upper(), f"Table {table_name} is missing PRIMARY KEY specification"

# 3. Foreign keys and relationships are correct
def test_3_foreign_keys_and_relationships(schema_sql):
    fk_checks = [
        ("job_roles", "departments(department_id)"),
        ("employees", "departments(department_id)"),
        ("employees", "job_roles(role_id)"),
        ("employees", "employees(employee_id)"),
        ("employee_skills", "employees(employee_id)"),
        ("employee_skills", "skills(skill_id)"),
        ("employee_history", "employees(employee_id)"),
        ("compensation_records", "employees(employee_id)"),
        ("performance_evaluations", "employees(employee_id)"),
        ("engagement_surveys", "employees(employee_id)"),
        ("projects", "departments(department_id)"),
        ("project_assignments", "projects(project_id)"),
        ("project_assignments", "employees(employee_id)"),
        ("time_off_records", "employees(employee_id)"),
        ("attrition_risk_scores", "employees(employee_id)"),
        ("retention_interventions", "employees(employee_id)"),
        ("exit_records", "employees(employee_id)"),
    ]
    for table, ref in fk_checks:
        escaped_ref = re.escape(ref)
        pattern = rf"REFERENCES\s+{escaped_ref}"
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing foreign key from {table} to {ref}"

# 4. Cardinalities and unique constraints are enforced
def test_4_cardinalities_and_uniqueness(schema_sql):
    # Exit records 1:1 with employee
    assert "employee_id VARCHAR(32) NOT NULL UNIQUE REFERENCES employees" in schema_sql
    # Unique compound keys
    assert "uq_dept_role_grade UNIQUE (department_id, title, grade_level)" in schema_sql
    assert "uq_emp_eval_cycle UNIQUE (employee_id, evaluation_cycle)" in schema_sql
    assert "uq_emp_survey_date UNIQUE (employee_id, survey_date)" in schema_sql
    assert "uq_emp_proj_start UNIQUE (employee_id, project_id, start_date)" in schema_sql
    assert "uq_emp_pred_date UNIQUE (employee_id, prediction_date)" in schema_sql

# 5. Effective dates and lifecycle states are defined
def test_5_effective_dates_and_lifecycle_states(schema_sql):
    for enum_name in MANDATORY_ENUMS:
        pattern = rf"CREATE\s+TYPE\s+{enum_name}\s+AS\s+ENUM"
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing ENUM: {enum_name}"
        
    date_constraints = [
        "probation_end_date IS NULL OR probation_end_date >= hire_date",
        "effective_to IS NULL OR effective_to >= effective_from",
        "end_date IS NULL OR end_date >= start_date",
        "action_date IS NULL OR action_date >= proposed_date",
        "outcome_evaluated_date IS NULL OR outcome_evaluated_date >= action_date",
    ]
    for constraint in date_constraints:
        assert constraint in schema_sql, f"Missing temporal constraint: {constraint}"

# 6. All fields are documented in the data dictionary
def test_6_all_fields_documented_in_data_dictionary(schema_sql, data_dict):
    tables = re.findall(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);",
        schema_sql,
        re.DOTALL | re.IGNORECASE
    )
    for table_name, body in tables:
        assert table_name in data_dict, f"Table {table_name} missing from data dictionary"
        for line in body.split("\n"):
            line = line.strip()
            if not line or line.startswith("--") or line.upper().startswith(("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", ")")):
                continue
            col_match = re.match(r"^([a-zA-Z0-9_]+)\s+", line)
            if col_match:
                col = col_match.group(1)
                assert f"`{col}`" in data_dict or col in data_dict, (
                    f"Column {table_name}.{col} not found in docs/data_dictionary.md"
                )

# 7. The four mandatory anomaly scenarios are covered
def test_7_four_anomaly_scenarios_covered(schema_sql):
    for view_name in ANOMALY_VIEWS:
        pattern = rf"CREATE\s+(OR\s+REPLACE\s+)?VIEW\s+{view_name}\s+AS"
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing anomaly view: {view_name}"
    
    # Check anomaly view logic
    assert "pa.start_date > ex.separation_date" in schema_sql # ANOM-01
    assert "WITH RECURSIVE HierarchyCTE" in schema_sql # ANOM-02
    assert "c.base_salary < r.min_salary OR c.base_salary > r.max_salary" in schema_sql # ANOM-03
    assert "t.is_approved = TRUE" in schema_sql and "pa.logged_hours_weekly > 0.00" in schema_sql # ANOM-04

# 8. Temporal integrity and historical event tracking are addressed
def test_8_temporal_integrity_and_event_tracking(schema_sql):
    # SCD Type 2 indexes
    assert "idx_emp_hist_active_single" in schema_sql
    assert "idx_comp_active_single" in schema_sql
    assert "WHERE is_current = TRUE" in schema_sql
    
    # Audit log ledger exists
    assert "CREATE TABLE IF NOT EXISTS audit_logs" in schema_sql
    assert "old_values JSONB" in schema_sql
    assert "new_values JSONB" in schema_sql
    
    # Trigger functions for updated_at
    assert "CREATE OR REPLACE FUNCTION trigger_set_timestamp()" in schema_sql
    assert "trg_emp_updated_at" in schema_sql
