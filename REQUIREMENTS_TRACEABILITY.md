# Workforce Retention Intelligence Platform (WorkforceIQ)
## Requirements Traceability Matrix (RTM)

**Project:** YottaFlex.ai Workforce Retention Intelligence Platform (`WorkforceIQ`)  
**Standard:** Enterprise Requirements Traceability Specification  
**Version:** 1.0.0  
**Phase:** Phase 1 Design Baseline  

---

## 1. Overview & Traceability Legend

This document establishes bidirectional traceability between high-level business requirements, domain entities, database tables, implementation source files, and automated test specifications. Every requirement defined in the YottaFlex.ai challenge is assigned a unique identifier (`REQ-XX` / `BR-XX`) and mapped throughout the system lifecycle.

### Requirement Status Legend:
- **DESIGNED:** Schema, data dictionary, and business rules established (Phase 1 Complete).
- **PLANNED:** Implementation targeted for subsequent development phases (Phases 2-6).
- **VERIFIED:** Fully implemented and validated via passing automated tests (Phase 7 Final).

---

## 2. Core Functional Requirements Traceability Matrix

| Req ID | Requirement Description | Domain Category | Database Entity / Table | Implementation File(s) | Test Specification File | Phase | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-ENT-01** | Model organizational departments with hierarchies, budget, and cost center attribution. | Org Structure | `departments` | `backend/models/department.py`, `database/schema.sql` | `tests/test_schema.py::test_departments_table` | Phase 1 | DESIGNED |
| **REQ-ENT-02** | Model standardized job roles, grade levels, pay bands (min/max), and exemption status. | Org Structure | `job_roles` | `backend/models/job_role.py`, `database/schema.sql` | `tests/test_schema.py::test_job_roles_table` | Phase 1 | DESIGNED |
| **REQ-ENT-03** | Model employee core profile, demographic info, hire date, status, tenure, and reporting structure. | Core Workforce | `employees` | `backend/models/employee.py`, `database/schema.sql` | `tests/test_schema.py::test_employees_table` | Phase 1 | DESIGNED |
| **REQ-ENT-04** | Track employee compensation history, base salary, bonus target, equity, and currency. | Total Rewards | `compensation_records` | `backend/models/compensation.py`, `database/schema.sql` | `tests/test_schema.py::test_compensation_table` | Phase 1 | DESIGNED |
| **REQ-ENT-05** | Track periodic performance reviews, goal achievements, promotion readiness, and evaluator ID. | Talent Mgmt | `performance_evaluations` | `backend/models/performance.py`, `database/schema.sql` | `tests/test_schema.py::test_performance_table` | Phase 1 | DESIGNED |
| **REQ-ENT-06** | Capture periodic employee engagement, eNPS, work-life balance, burnout risk, and sentiment. | Engagement | `engagement_surveys` | `backend/models/engagement.py`, `database/schema.sql` | `tests/test_schema.py::test_engagement_table` | Phase 1 | DESIGNED |
| **REQ-ENT-07** | Model project portfolio, billable staffing, employee assignment allocations, and duration. | Operations | `projects`, `project_assignments` | `backend/models/project.py`, `database/schema.sql` | `tests/test_schema.py::test_projects_table` | Phase 1 | DESIGNED |
| **REQ-ENT-08** | Store ML-driven flight risk scores, probability tiers (Low/Med/High/Critical), and top SHAP risk factors. | Predictive AI | `attrition_risk_scores` | `ml/train.py`, `backend/models/risk.py`, `database/schema.sql` | `tests/test_ml_pipeline.py::test_risk_scoring` | Phase 1 | DESIGNED |
| **REQ-ENT-09** | Orchestrate retention interventions, workflows, approval status, investment cost, and outcome. | Retention Ops | `retention_interventions` | `backend/models/intervention.py`, `database/schema.sql` | `tests/test_schema.py::test_interventions_table` | Phase 1 | DESIGNED |
| **REQ-ENT-10** | Record formal employee separations, separation type (voluntary/involuntary), regret status, and exit interview. | Offboarding | `exit_records` | `backend/models/exit_record.py`, `database/schema.sql` | `tests/test_schema.py::test_exit_records_table` | Phase 1 | DESIGNED |
| **REQ-SUP-01** | Capture technical and domain skill master catalog and employee proficiency levels. | Skills Matrix | `skills`, `employee_skills` | `backend/models/skill.py`, `database/schema.sql` | `tests/test_schema.py::test_skills_bridge` | Phase 1 | DESIGNED |
| **REQ-SUP-02** | Maintain longitudinal SCD Type 2 history for employee title, department, status, and manager changes. | Temporal History | `employee_history` | `database/schema.sql`, `backend/services/history_service.py` | `tests/test_schema.py::test_scd2_history` | Phase 1 | DESIGNED |
| **REQ-SUP-03** | Record all system mutations, user access, and configuration updates in an append-only audit trail. | Governance | `audit_logs` | `database/schema.sql`, `backend/services/audit_service.py` | `tests/test_schema.py::test_audit_logging` | Phase 1 | DESIGNED |
| **REQ-SUP-04** | Quarantine data validation errors and isolated organizational anomalies. | Data Quality | `data_anomalies` | `database/schema.sql`, `validation/anomaly_detector.py` | `tests/test_schema.py::test_data_anomalies` | Phase 1 | DESIGNED |
| **REQ-SUP-05** | Track approved and pending employee time-off and leave to validate operational activity. | Operations | `time_off_records` | `backend/models/time_off.py`, `database/schema.sql` | `tests/test_schema.py::test_time_off_records` | Phase 1 | DESIGNED |

---

## 3. Four Mandatory Anomaly Scenarios Traceability

| Anomaly ID | Scenario Name & Description | Integrity Rule | Schema Enforcement / Query View | Detection & Ingestion Logic | Test Verification Function |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ANOM-01** | **Post-Termination Activity:** Employee marked as Terminated records billable project hours, submits survey responses, or has active payroll generated after separation date. | `BR-ANOM-01`: Event timestamp MUST be <= Employee `separation_date`. | View: `v_anomaly_post_termination_activity`, Check constraint on activity dates. | `data_generator/anomalies.py::inject_post_termination_activity`, `validation/anomaly_detector.py` | `tests/test_business_rules.py::test_anomaly_post_termination_detection` |
| **ANOM-02** | **Circular Management Hierarchy & Orphan Reporting:** Cyclic supervisor chains (e.g. A reports to B, B reports to C, C reports to A) or active non-executives with null/self-reporting manager IDs. | `BR-ANOM-02`: Reporting hierarchy MUST form a directed acyclic graph (DAG) rooted at CEO. | View: `v_anomaly_circular_hierarchy`, Recursive CTE acyclicity check. | `data_generator/anomalies.py::inject_circular_hierarchy`, `validation/anomaly_detector.py` | `tests/test_business_rules.py::test_anomaly_circular_hierarchy_detection` |
| **ANOM-03** | **Compensation Inversion & Grade Band Breach:** Base salary falls strictly outside the role grade band `[min_salary, max_salary]`, or junior subordinate earns significantly more than senior supervisor (>25% inversion). | `BR-ANOM-03`: `base_salary BETWEEN min_salary AND max_salary`; junior salary < senior salary adjusted for role. | View: `v_anomaly_salary_band_breach`, Check constraints on role grade ranges. | `data_generator/anomalies.py::inject_compensation_inversion`, `validation/anomaly_detector.py` | `tests/test_business_rules.py::test_anomaly_compensation_inversion_detection` |
| **ANOM-04** | **Conflicting Leave & Billable Project Logging / Impossible Hours:** Employee logs full-time billable project hours on dates with approved full-day sick/bereavement leave, or logs >80 hours in a single week. | `BR-ANOM-04`: Sum of billable hours on approved full leave date MUST = 0; weekly hours <= 80. | View: `v_anomaly_leave_hour_conflict`, Trigger-based validation check. | `data_generator/anomalies.py::inject_impossible_hours_and_leave_conflict`, `validation/anomaly_detector.py` | `tests/test_business_rules.py::test_anomaly_leave_conflict_detection` |

---

## 4. Business Logic & Lifecycle State Machine Traceability

| Rule ID | Business Rule Description | Governing Entity | Implementation Mechanism | Test Verification Function |
| :--- | :--- | :--- | :--- | :--- |
| **BR-LC-01** | Employee lifecycle states: `APPLICANT` -> `ACTIVE` -> `ON_LEAVE` -> `NOTICE_PERIOD` -> `TERMINATED` / `RETIRED`. Illegal jumps (e.g. `TERMINATED` -> `ACTIVE` without rehire flow) are rejected. | `employees`, `employee_history` | PostgreSQL ENUM `employment_status_enum`, State Transition Validator | `tests/test_business_rules.py::test_employee_lifecycle_transitions` |
| **BR-TMP-01** | SCD Type 2 temporal integrity: `effective_from` < `effective_to`. Exactly one active record (`is_current = TRUE` and `effective_to IS NULL`) per employee. | `employee_history`, `compensation_records` | Check constraints, Partial Unique Index on `(employee_id) WHERE is_current = TRUE` | `tests/test_business_rules.py::test_scd2_temporal_invariants` |
| **BR-ATT-01** | Exit record consistency: When `employees.status = 'TERMINATED'`, an `exit_records` row MUST exist with matching `separation_date`, valid `separation_type`, and `regret_status`. | `employees`, `exit_records` | Referential foreign key, Cross-table consistency validator | `tests/test_business_rules.py::test_attrition_outcome_consistency` |
| **BR-INT-01** | Retention intervention lifecycle: `RECOMMENDED` -> `APPROVED` -> `OFFERED` -> `ACCEPTED` / `DECLINED` -> `EFFECTIVE` -> `EVALUATED`. Cost and ROI must be tracked. | `retention_interventions` | PostgreSQL ENUM `intervention_status_enum`, Intervention workflow service | `tests/test_business_rules.py::test_intervention_workflow_lifecycle` |
| **BR-PRJ-01** | Project assignment allocation bounds: Individual employee allocation per project MUST be between 1% and 100%. Total concurrent allocation across projects SHOULD NOT exceed 120%. | `project_assignments` | Check constraint `allocation_percentage BETWEEN 1 AND 100`, Cross-project validation check | `tests/test_business_rules.py::test_project_allocation_limits` |

---

## 5. System Components & Deliverable Mapping

| Component Module | Planned Source Files | Description of Deliverables | Corresponding Test File |
| :--- | :--- | :--- | :--- |
| **Database & Schema** | `database/schema.sql` | DDL script defining 15 tables, 8 ENUMs, 4 views, 5 indexes, and trigger functions. | `tests/test_schema.py` |
| **Synthetic Generator** | `data_generator/generator.py`, `data_generator/anomalies.py`, `data_generator/config.py` | Synthetic cohort generation (1,000-5,000 agents), statistical distributions, anomaly injection. | `tests/test_data_generator.py` |
| **Data Quality Engine** | `validation/validators.py`, `validation/anomaly_detector.py` | Pydantic schema validation, business rule enforcement, exception isolation. | `tests/test_business_rules.py` |
| **Machine Learning** | `ml/train.py`, `ml/features.py`, `ml/explain.py`, `ml/evaluate.py` | Attrition prediction model (ROC-AUC >= 0.85), SHAP explainability pipeline, risk scoring. | `tests/test_ml_pipeline.py` |
| **Backend REST API** | `backend/main.py`, `backend/routes/*.py`, `backend/services/*.py` | FastAPI endpoints for Employee 360, retention analytics, flight risk watchlist, interventions. | `tests/test_api_endpoints.py` |
| **Streamlit Dashboard**| `dashboard/app.py`, `dashboard/pages/*.py` | Multi-page executive and HRBP analytics application with Plotly visualizations. | `tests/test_dashboard_e2e.py` |

---

## 6. Verification and Sign-Off Gates

- **Gate 1 (Phase 1):** Complete specifications and verified database schema (`schema.sql` passes DDL parsing with zero errors).
- **Gate 2 (Phase 2):** Successful generation of synthetic dataset with 100% anomaly ground-truth correspondence.
- **Gate 3 (Phase 3):** Full ingestion into PostgreSQL with 0 unhandled exceptions; all injected anomalies routed to `data_anomalies`.
- **Gate 4 (Phase 4):** ML Model achieves ROC-AUC >= 0.85 on test split with valid global and local SHAP summary values.
- **Gate 5 (Phase 5):** All FastAPI endpoints operational with automated Swagger docs and HTTP status 200/201 responses.
- **Gate 6 (Phase 6):** Complete Streamlit interactive dashboard operational with sub-second page rendering.
- **Gate 7 (Phase 7):** Comprehensive test suite passes with >=90% line coverage.
