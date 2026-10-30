# WorkforceIQ — Data Validation Strategy

> **Phase 4 Document** | Version 1.0 | 2026-10-30

---

## 1. Overview

This document defines the comprehensive data validation strategy employed in the
WorkforceIQ Workforce Retention Intelligence platform. Validation is structured
around **12 pillars** that cover every dimension of data quality from primary key
integrity through temporal leakage detection.

The validation engine is implemented in
[`validation/comprehensive_validator.py`](../validation/comprehensive_validator.py)
and is invoked automatically by the CI pipeline and by Phase 4 test suites.

---

## 2. Validation Architecture

```
data/generated/*.csv          data/ground_truth/*.csv
        │                              │
        └──────────────┬──────────────┘
                       │
          ┌────────────▼─────────────┐
          │  run_comprehensive_      │
          │  validation()            │
          │  (12-Pillar Engine)      │
          └────────────┬─────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  data/manifests/            │
        │  validation_summary.json   │
        └─────────────────────────────┘
```

The engine loads all exported CSV files into in-memory pandas DataFrames,
executes each pillar independently, collects per-pillar results, and returns
a structured summary dictionary. The engine does **not** modify any source data.

---

## 3. The 12 Validation Pillars

### Pillar 1 — Primary-Key Uniqueness

**Rule:** Every table's primary key column must contain no duplicate values.

| Table | Primary Key |
|---|---|
| `departments` | `department_id` |
| `job_roles` | `role_id` |
| `skills` | `skill_id` |
| `employees` | `employee_id` |
| `compensation_records` | `compensation_id` |
| `performance_evaluations` | `evaluation_id` |
| `engagement_surveys` | `survey_id` |
| `projects` | `project_id` |
| `project_assignments` | `assignment_id` |
| `time_off_records` | `leave_id` |
| `attrition_risk_scores` | `score_id` |
| `retention_interventions` | `intervention_id` |
| `exit_records` | `exit_id` |
| `data_anomalies` | `anomaly_id` |

**Detection method:** `df[pk_col].nunique() == len(df)` for every table.

**Failure response:** List all tables with duplicate primary keys.

---

### Pillar 2 — Foreign-Key Integrity

**Rule:** Every foreign key value must exist in the referenced parent table.

| Child Table | Foreign Key | Parent Table |
|---|---|---|
| `employees` | `department_id` | `departments` |
| `employees` | `role_id` | `job_roles` |
| `compensation_records` | `employee_id` | `employees` |
| `performance_evaluations` | `employee_id` | `employees` |
| `engagement_surveys` | `employee_id` | `employees` |
| `project_assignments` | `employee_id` | `employees` |
| `project_assignments` | `project_id` | `projects` |
| `exit_records` | `employee_id` | `employees` |

**Detection method:** `child_df[fk_col].isin(parent_id_set).all()`

**Failure response:** Report every broken FK relationship by name.

---

### Pillar 3 — Allowed Enum Validation

**Rule:** Categorical columns must only contain values from their defined domain.

| Column | Allowed Values |
|---|---|
| `employees.status` | APPLICANT, ONBOARDING, ACTIVE, ON\_LEAVE, NOTICE\_PERIOD, TERMINATED, RETIRED |
| `employees.employment_type` | FULL\_TIME, PART\_TIME, CONTRACTOR, INTERN |
| `employees.work_location` | ONSITE, HYBRID, REMOTE |
| `exit_records.separation_type` | VOLUNTARY, INVOLUNTARY, RETIREMENT, CONTRACT\_END |
| `exit_records.regret_status` | REGRETTABLE, NON\_REGRETTABLE, UNDETERMINED |
| `attrition_risk_scores.risk_tier` | LOW, MEDIUM, HIGH, CRITICAL |
| `retention_interventions.intervention_type` | 7 approved types |
| `performance_evaluations.rating` | UNSATISFACTORY … OUTSTANDING (5 levels) |

**Detection method:** `set(df[col]).issubset(VALID_ENUMS[enum_key])`

---

### Pillar 4 — Date Ordering

**Rule:** All date pairs must satisfy their natural ordering constraint.

| Constraint | Table |
|---|---|
| `hire_date` ≤ `separation_date` | employees + exit_records |
| `start_date` ≤ `end_date` | project_assignments |
| `start_date` ≤ `end_date` | time_off_records |

**Detection method:** Boolean series comparison after parsing dates as strings
(lexicographic ordering valid for ISO-8601 YYYY-MM-DD format).

---

### Pillar 5 — Effective-Date Consistency (SCD Type 2)

**Rule:** The `compensation_records` table implements SCD Type 2 history:
- Every **active** employee (`is_active=True`) must have **exactly one**
  compensation record with `is_current=True`.
- For every **closed** compensation record (`effective_to` is not null),
  `effective_to` ≥ `effective_from`.

**Why this matters:** SCD2 violations produce invalid compa-ratio calculations
and break the salary history timeline used by the ML model.

**Detection method:** GroupBy `employee_id` for active employees, assert size = 1;
filter closed records and compare date columns.

---

### Pillar 6 — Duplicate Detection

**Rule:** The following uniqueness constraints must hold:
- `employees.email` must be unique across all records (corporate email uniqueness).
- `(employee_id, skill_id)` composite key must be unique in `employee_skills`.
- `employee_id` must be unique in `exit_records` (1:1 lifecycle constraint).

**Detection method:** `df[col].duplicated().any()` and composite key checks.

---

### Pillar 7 — Arithmetic Reconciliation

**Rule A — Compa-Ratio Formula:**
For every row in `derived_workforce_features`:
```
compa_ratio ≈ base_salary / role_mid_salary  (tolerance ±0.005)
```

**Rule B — Performance Correlation:**
The Pearson correlation between `numeric_score` and `goals_met_pct` in
`performance_evaluations` must exceed **0.80**, confirming that the simulation
is internally consistent (higher-scoring reviews must align with higher goal
achievement rates).

**Observed correlation (10k dataset):** > 0.95

---

### Pillar 8 — Lifecycle Transition Validation

**Rule:** An employee's status lifecycle must follow legal transitions:

```
ONBOARDING → ACTIVE → ON_LEAVE → ACTIVE → NOTICE_PERIOD → TERMINATED
                                                         → RETIRED
```

**Enforcement:** Every employee with `status = TERMINATED` must have a
corresponding record in `exit_records`. Orphaned terminations without exit
records violate referential integrity and produce null outcome labels in ML.

**Detection method:** Set difference `terminated_ids - exit_emp_ids`

---

### Pillar 9 — Missing-Value Handling

**Rule:** Mandatory columns must never be null. Allowable nullable columns are
documented and treated with domain-appropriate defaults (neutral prior 3.5 for
missing engagement scores; 0.25 burnout index).

**Mandatory non-null columns audited:**

| Column | Table |
|---|---|
| `email` | employees |
| `hire_date` | employees |
| `min_salary` | job_roles |
| `base_salary` | compensation_records |
| `numeric_score` | performance_evaluations |
| `flight_risk_prob` | attrition_risk_scores |

**Missing survey handling:** Employees with zero submitted surveys receive
`avg_job_satisfaction = 3.5` and `latest_burnout = 0.25` — verified neutral
prior values confirmed by Pillar 2 of anomaly verification.

---

### Pillar 10 — Attrition Outcome Consistency

**Rule:** The set of employee IDs with `separation_type = VOLUNTARY` in
`exit_records` must be **exactly equal** to the set of employee IDs with
`has_attrited_voluntary = True` in `attrition_labels`.

This cross-table consistency check prevents label mismatches that would corrupt
binary classification metrics during ML evaluation.

**Detection method:** Python set equality comparison.

---

### Pillar 11 — Temporal Leakage Detection

**Rule:** The `derived_workforce_features` table (used as ML model input) must
contain **zero** post-outcome columns. Forbidden features:

| Forbidden Column | Reason |
|---|---|
| `separation_date` | Known only after termination event |
| `has_attrited` | The prediction target |
| `separation_type` | Post-outcome classification |
| `exit_id` | Only exists for terminated employees |

**Detection method:** `set(forbidden).intersection(set(derived_df.columns))`

**Observed result (10k dataset):** 0 leaked features in 13-column derived table.

---

### Pillar 12 — Valid Joins Across All Entities

**Rule:** The core entity graph must be fully traversable:
- All 10,000 employees must inner-join 100% to `departments` and `job_roles`.
- All **active** employees must inner-join 100% to their `is_current=True`
  compensation record.
- All **terminated** employees must inner-join 100% to `exit_records`.
- All `project_assignments` rows must inner-join 100% to both `projects`
  and `employees`.

**Why this matters:** Broken joins produce NULL-inflated ML features and silently
exclude employees from cohort analyses.

---

## 4. Validation Execution

### Command-Line Execution

```bash
# Full 12-pillar validation (reads existing data/generated/*.csv)
python -m validation.comprehensive_validator

# Export validation summary manifest
python scratch/generate_manifests.py
```

### Pytest Automation

```bash
# Run all 42 validation tests
pytest tests/test_validation.py -v

# Include full suite (89 tests total)
pytest -v
```

### Output Artifacts

| File | Description |
|---|---|
| `data/manifests/validation_summary.json` | Full 12-pillar result with all sub-checks |
| `data/manifests/source_manifest.json` | SHA-256 + byte-size for all dataset files |

---

## 5. Validation Results (10,000-Employee Dataset)

| Pillar | Status | Key Metric |
|---|---|---|
| 1. Primary-Key Uniqueness | ✅ PASSED | 14 tables checked, 0 violations |
| 2. Foreign-Key Integrity | ✅ PASSED | 8 relationships verified, 0 broken |
| 3. Allowed Enum Validation | ✅ PASSED | 8 enums verified, 0 invalid values |
| 4. Date Ordering | ✅ PASSED | 3 date-pair constraints, 0 violations |
| 5. Effective-Date Consistency | ✅ PASSED | 8,813 active comp records, 0 SCD violations |
| 6. Duplicate Detection | ✅ PASSED | 0 duplicate emails, 0 duplicate exits |
| 7. Arithmetic Reconciliation | ✅ PASSED | compa-ratio exact; perf corr > 0.95 |
| 8. Lifecycle Transitions | ✅ PASSED | All 1,187 terminated employees have exits |
| 9. Missing-Value Handling | ✅ PASSED | 0 nulls in 6 mandatory columns |
| 10. Attrition Consistency | ✅ PASSED | Exit set == Label set (exact match) |
| 11. Temporal Leakage | ✅ PASSED | 0 forbidden features in derived table |
| 12. Valid Joins | ✅ PASSED | 100% join coverage across all 3 entity graphs |

**Overall: 12/12 PASSED — 0 violations**

---

## 6. Failure Handling Protocol

| Severity | Condition | Response |
|---|---|---|
| **CRITICAL** | PK violation / broken FK / temporal leakage | Block pipeline; do not export |
| **HIGH** | SCD2 violation / lifecycle mismatch | Log error; alert on-call team |
| **MEDIUM** | Enum violation / duplicate detection | Log warning; quarantine affected rows |
| **LOW** | Arithmetic tolerance exceeded | Log warning; flag derived column |

In the automated test suite (`tests/test_validation.py`), **any pillar failure
causes the test to fail with a descriptive assertion message** identifying the
specific table, column, and violation count.

---

## 7. Extension Points

To add a new validation rule:

1. Add the check inside `run_comprehensive_validation()` in
   [`validation/comprehensive_validator.py`](../validation/comprehensive_validator.py).
2. Record the result in `pillar_results` with `status: PASSED/FAILED`.
3. Add corresponding test class in
   [`tests/test_validation.py`](../tests/test_validation.py).
4. Re-run `python scratch/generate_manifests.py` to refresh `validation_summary.json`.
