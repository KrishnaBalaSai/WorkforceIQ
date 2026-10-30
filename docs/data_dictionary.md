# Workforce Retention Intelligence Platform (WorkforceIQ)
## Enterprise Data Dictionary & Technical Schema Specification

**System Name:** Workforce Retention Intelligence System (`WorkforceIQ`)  
**Organization:** YottaFlex.ai Enterprise Analytics  
**Version:** 1.0.0  
**Phase:** Phase 1 Design Baseline  

---

## 1. Schema Overview & Domain Structure

The `WorkforceIQ` data model is organized into five cohesive relational domains designed to track human capital lifecycles with absolute temporal fidelity:
1. **Organizational & Core Workforce Domain:** `departments`, `job_roles`, `employees`, `skills`, `employee_skills`.
2. **Total Rewards & Performance Domain:** `compensation_records`, `performance_evaluations`.
3. **Operations & Sentiment Domain:** `engagement_surveys`, `projects`, `project_assignments`, `time_off_records`.
4. **Predictive Retention & Separation Domain:** `attrition_risk_scores`, `retention_interventions`, `exit_records`.
5. **System Governance, Temporal & Anomaly Domain:** `employee_history` (SCD Type 2), `audit_logs`, `data_anomalies`.

---

## 2. Global Enumerated Data Types (ENUMs)

| Enum Name | Values | Business Context |
| :--- | :--- | :--- |
| `employment_status_enum` | `'APPLICANT'`, `'ONBOARDING'`, `'ACTIVE'`, `'ON_LEAVE'`, `'NOTICE_PERIOD'`, `'TERMINATED'`, `'RETIRED'` | Tracks employee lifecycle state in the organization. |
| `employment_type_enum` | `'FULL_TIME'`, `'PART_TIME'`, `'CONTRACTOR'`, `'INTERN'` | Distinguishes worker classification and benefits eligibility. |
| `work_location_enum` | `'ONSITE'`, `'HYBRID'`, `'REMOTE'` | Identifies employee working arrangement. |
| `separation_type_enum` | `'VOLUNTARY'`, `'INVOLUNTARY'`, `'RETIREMENT'`, `'CONTRACT_END'` | Primary classification for employee offboarding events. |
| `regret_status_enum` | `'REGRETTABLE'`, `'NON_REGRETTABLE'`, `'UNDETERMINED'` | Organizational assessment of the impact of an attrition loss. |
| `risk_tier_enum` | `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'` | Categorical grouping of ML-predicted attrition probability. |
| `intervention_type_enum`| `'COMPENSATION_INCREASE'`, `'RETENTION_BONUS'`, `'ROLE_PROMOTION'`, `'PROJECT_REASSIGNMENT'`, `'FLEXIBLE_WORK_SCHEDULE'`, `'EXECUTIVE_MENTORSHIP'`, `'CAREER_DEVELOPMENT'` | Standardized retention action categories. |
| `intervention_status_enum`| `'RECOMMENDED'`, `'APPROVED'`, `'REJECTED'`, `'OFFERED'`, `'ACCEPTED'`, `'DECLINED'`, `'COMPLETED'`, `'FAILED'` | Workflow lifecycle state for retention interventions. |
| `review_rating_enum` | `'UNSATISFACTORY'`, `'NEEDS_IMPROVEMENT'`, `'MEETS_EXPECTATIONS'`, `'EXCEEDS_EXPECTATIONS'`, `'OUTSTANDING'` | Standard 5-tier employee performance appraisal ratings. |
| `anomaly_type_enum` | `'POST_TERMINATION_ACTIVITY'`, `'CIRCULAR_HIERARCHY'`, `'COMPENSATION_INVERSION'`, `'LEAVE_HOUR_CONFLICT'`, `'SCHEMA_VIOLATION'`, `'DATA_LEAKAGE'` | Classification for automated data quality & integrity exceptions. |
| `severity_level_enum` | `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'` | Urgency and impact level for detected data anomalies. |
| `leave_type_enum` | `'ANNUAL'`, `'SICK'`, `'MATERNITY'`, `'PATERNITY'`, `'BEREAVEMENT'`, `'UNPAID'` | Categories of employee absence. |

---

## 3. Data Dictionary: Core & Supporting Entities

### 3.1 Entity 1: `departments` (Organizational Units)
*Represents cost centers, business units, and organizational hierarchies.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `department_id` | `VARCHAR(32)` | No | PK | - | Unique department code (e.g., `DEP-ENG-01`). Format: `^DEP-[A-Z0-9_-]{2,20}$`. |
| `name` | `VARCHAR(100)` | No | UNIQUE | - | Department name (e.g., `Software Engineering`, `Enterprise Sales`). |
| `division` | `VARCHAR(100)` | No | - | - | High-level division (e.g., `Product & Engineering`, `Go-To-Market`). |
| `cost_center_code` | `VARCHAR(32)` | No | UNIQUE | - | Financial accounting cost center code. |
| `head_employee_id` | `VARCHAR(32)` | Yes | FK (`employees.employee_id`) | NULL | Employee ID of the department leader / VP. Nullable to prevent circular creation. |
| `parent_department_id`| `VARCHAR(32)` | Yes | FK (`departments.department_id`) | NULL | Hierarchical parent department for sub-units. |
| `annual_budget` | `NUMERIC(14, 2)`| No | CHECK (`annual_budget >= 0`) | `0.00` | Allocated annual operational budget in USD. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System creation audit timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System update audit timestamp. |

- **Cardinality:**
  - One Department has Many Employees (`1:N`).
  - One Department has Many Job Roles (`1:N`).
  - One Department has Many Projects (`1:N`).

---

### 3.2 Entity 2: `job_roles` (Job Titles & Grades)
*Defines job profiles, seniority grade levels, salary bands, and market benchmarks.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `role_id` | `VARCHAR(32)` | No | PK | - | Unique role identifier (e.g., `ROLE-SWE-03`). |
| `department_id` | `VARCHAR(32)` | No | FK (`departments.department_id`) | - | Department to which this role belongs. |
| `title` | `VARCHAR(100)` | No | - | - | Formal title (e.g., `Senior Staff Software Engineer`). |
| `grade_level` | `INTEGER` | No | CHECK (`grade_level BETWEEN 1 AND 15`) | - | Numerical seniority tier (e.g., 1=Junior, 5=Senior, 8=Principal, 10=Director). |
| `min_salary` | `NUMERIC(12, 2)`| No | CHECK (`min_salary >= 0`) | - | Minimum base salary allowed for this grade level. |
| `mid_salary` | `NUMERIC(12, 2)`| No | CHECK (`mid_salary >= min_salary`) | - | Market midpoint salary used for compa-ratio calculations. |
| `max_salary` | `NUMERIC(12, 2)`| No | CHECK (`max_salary >= mid_salary`)| - | Maximum base salary allowed for this grade level. |
| `is_exempt` | `BOOLEAN` | No | - | `TRUE` | FLSA overtime exemption flag. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System creation audit timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System update audit timestamp. |

- **Cardinality:**
  - One Job Role belongs to One Department (`N:1`).
  - One Job Role has Many Employees (`1:N`).
  - One Job Role is referenced by Many History snapshots (`1:N`).

---

### 3.3 Entity 3: `employees` (Master Worker Profile)
*The central entity representing current and past employees.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `employee_id` | `VARCHAR(32)` | No | PK | - | Enterprise worker ID (e.g., `EMP-001042`). Format: `^EMP-[0-9]{6}$`. |
| `first_name` | `VARCHAR(50)` | No | - | - | Employee first/given name. |
| `last_name` | `VARCHAR(50)` | No | - | - | Employee last/family name. |
| `email` | `VARCHAR(100)` | No | UNIQUE | - | Corporate corporate email (`^[a-zA-Z0-9._%+-]+@yottaflex\.ai$`). |
| `department_id` | `VARCHAR(32)` | No | FK (`departments.department_id`) | - | Current department. |
| `role_id` | `VARCHAR(32)` | No | FK (`job_roles.role_id`) | - | Current job role. |
| `manager_id` | `VARCHAR(32)` | Yes | FK (`employees.employee_id`) | NULL | Direct supervisor. NULL only for the Chief Executive Officer. |
| `status` | `employment_status_enum` | No | - | `'ACTIVE'` | Current lifecycle status. |
| `employment_type` | `employment_type_enum` | No | - | `'FULL_TIME'` | Classification type. |
| `work_location` | `work_location_enum` | No | - | `'HYBRID'` | Work location model. |
| `hire_date` | `DATE` | No | - | - | Official commencement date. |
| `probation_end_date`| `DATE` | Yes | CHECK (`probation_end_date >= hire_date`) | NULL | Scheduled completion of initial probation. |
| `is_active` | `BOOLEAN` | No | - | `TRUE` | Fast-query active flag (`status IN ('ACTIVE', 'ON_LEAVE', 'NOTICE_PERIOD')`). |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System creation timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System update timestamp. |

- **Cardinality:**
  - Employee belongs to One Department (`N:1`).
  - Employee has One Current Role (`N:1`).
  - Employee reports to One Manager (`N:1 self-referential`).
  - Employee has Many Compensation Records (`1:N`).
  - Employee has Many Performance Evaluations (`1:N`).
  - Employee has Many Engagement Surveys (`1:N`).
  - Employee has Many Project Assignments (`1:N`).
  - Employee has Many Risk Scores (`1:N`).
  - Employee has Many Interventions (`1:N`).
  - Employee has Zero or One Exit Record (`1:0..1`).
  - Employee has Many Historical Snapshots (`1:N`).

---

### 3.4 Entity 4: `compensation_records` (Total Rewards History)
*Maintains longitudinal compensation records, base salaries, bonuses, and equity grants.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `compensation_id` | `UUID` | No | PK | `gen_random_uuid()` | Universally unique compensation event identifier. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Associated employee. |
| `base_salary` | `NUMERIC(12, 2)`| No | CHECK (`base_salary > 0`) | - | Annualized gross base salary. |
| `bonus_target_pct` | `NUMERIC(5, 2)` | No | CHECK (`bonus_target_pct BETWEEN 0 AND 100`)| `0.00` | Target incentive bonus percentage of base salary. |
| `stock_options_granted` | `INTEGER` | No | CHECK (`stock_options_granted >= 0`) | `0` | Equity / RSU shares awarded in this grant. |
| `currency` | `VARCHAR(3)` | No | CHECK (`length(currency) = 3`) | `'USD'` | ISO 4217 3-letter currency code. |
| `effective_from` | `DATE` | No | - | - | Date when this salary package took effect. |
| `effective_to` | `DATE` | Yes | CHECK (`effective_to IS NULL OR effective_to >= effective_from`) | NULL | Expiration date of this compensation tranche. |
| `is_current` | `BOOLEAN` | No | - | `TRUE` | Indicates currently active compensation. |
| `revision_reason` | `VARCHAR(100)`| No | - | `'ANNUAL_REVIEW'`| Reason: `'HIRE'`, `'ANNUAL_REVIEW'`, `'PROMOTION'`, `'RETENTION'`, `'MARKET_ADJUSTMENT'`. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System creation timestamp. |

- **Cardinality:** One Employee has Many Compensation Records (`1:N`). Exactly one row has `is_current = TRUE`.

---

### 3.5 Entity 5: `performance_evaluations` (Talent Appraisals)
*Periodic formal performance reviews, goal achievement rates, and promotion readiness.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `evaluation_id` | `UUID` | No | PK | `gen_random_uuid()` | Evaluation identifier. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Employee being reviewed. |
| `reviewer_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Reviewer (typically direct manager). |
| `evaluation_cycle` | `VARCHAR(32)` | No | - | - | Review cycle code (e.g., `'2025-H1'`, `'2025-Q4'`). |
| `rating` | `review_rating_enum` | No | - | - | Formal evaluation score. |
| `numeric_score` | `NUMERIC(3, 2)` | No | CHECK (`numeric_score BETWEEN 1.00 AND 5.00`) | - | Continuous 1.00 to 5.00 performance score. |
| `goals_met_pct` | `NUMERIC(5, 2)` | No | CHECK (`goals_met_pct BETWEEN 0 AND 150`) | - | Objective achievement rate (allows >100% for overachievement). |
| `promotion_readiness` | `VARCHAR(32)` | No | CHECK (`promotion_readiness IN ('NOT_READY', 'DEVELOPING', 'READY_NOW', 'PROMOTED')`) | `'DEVELOPING'` | Talent pipeline readiness category. |
| `feedback_summary` | `TEXT` | Yes | - | NULL | Manager review narrative and qualitative remarks. |
| `evaluation_date` | `DATE` | No | - | - | Date evaluation was officially finalized. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |

- **Cardinality:** One Employee has Many Performance Evaluations (`1:N`).

---

### 3.6 Entity 6: `engagement_surveys` (Pulse & Sentiment)
*Longitudinal employee engagement, sentiment, burnout indices, and satisfaction metrics.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | `UUID` | No | PK | `gen_random_uuid()` | Survey record identifier. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Responding employee. |
| `survey_date` | `DATE` | No | - | - | Date survey was completed. |
| `enps_score` | `INTEGER` | No | CHECK (`enps_score BETWEEN 0 AND 10`) | - | Employee Net Promoter Score question (0-10). |
| `job_satisfaction` | `INTEGER` | No | CHECK (`job_satisfaction BETWEEN 1 AND 5`) | - | Job satisfaction Likert scale (1=Very Dissatisfied, 5=Very Satisfied). |
| `work_life_balance` | `INTEGER` | No | CHECK (`work_life_balance BETWEEN 1 AND 5`) | - | Work-life balance Likert score (1-5). |
| `management_trust` | `INTEGER` | No | CHECK (`management_trust BETWEEN 1 AND 5`) | - | Confidence and trust in direct leadership (1-5). |
| `career_growth_opps` | `INTEGER` | No | CHECK (`career_growth_opps BETWEEN 1 AND 5`) | - | Perceived career development opportunities (1-5). |
| `burnout_risk_index`| `NUMERIC(3, 2)` | No | CHECK (`burnout_risk_index BETWEEN 0.00 AND 1.00`) | - | Composite burnout risk score (0.00=No Burnout, 1.00=Severe Burnout). |
| `sentiment_score` | `NUMERIC(3, 2)` | No | CHECK (`sentiment_score BETWEEN -1.00 AND 1.00`) | - | NLP-extracted sentiment from freeform feedback (-1.0 to +1.0). |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |

- **Cardinality:** One Employee has Many Engagement Surveys (`1:N`).

---

### 3.7 Entity 7: `projects` and `project_assignments` (Operational Allocation)
*Tracks project initiatives and employee operational workloads.*

#### 3.7.1 Table: `projects`
| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `project_id` | `VARCHAR(32)` | No | PK | - | Project identifier (e.g., `PRJ-ALPHA-2025`). |
| `department_id` | `VARCHAR(32)` | No | FK (`departments.department_id`) | - | Owning department. |
| `name` | `VARCHAR(100)` | No | - | - | Commercial/technical project name. |
| `priority` | `VARCHAR(20)` | No | CHECK (`priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')`) | `'MEDIUM'` | Business priority. |
| `start_date` | `DATE` | No | - | - | Project kickoff date. |
| `end_date` | `DATE` | Yes | CHECK (`end_date IS NULL OR end_date >= start_date`) | NULL | Anticipated or actual completion date. |
| `is_billable` | `BOOLEAN` | No | - | `TRUE` | Whether client billable or internal R&D. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |

#### 3.7.2 Table: `project_assignments` (Bridge)
| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `UUID` | No | PK | `gen_random_uuid()` | Assignment identifier. |
| `project_id` | `VARCHAR(32)` | No | FK (`projects.project_id`) | - | Assigned project. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Assigned worker. |
| `role_in_project` | `VARCHAR(50)` | No | - | `'CONTRIBUTOR'`| Role (e.g., `'TECH_LEAD'`, `'CONTRIBUTOR'`, `'QA'`). |
| `allocation_pct` | `INTEGER` | No | CHECK (`allocation_pct BETWEEN 1 AND 100`) | `100` | Percentage of weekly hours allocated to this project. |
| `logged_hours_weekly`| `NUMERIC(5, 2)`| No | CHECK (`logged_hours_weekly >= 0.00`) | `40.00` | Average billable hours logged per week. |
| `start_date` | `DATE` | No | - | - | Assignment start date. |
| `end_date` | `DATE` | Yes | CHECK (`end_date IS NULL OR end_date >= start_date`) | NULL | Assignment release date. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |

---

### 3.8 Entity 8: `attrition_risk_scores` (Predictive Flight Risk)
*Stores machine learning retention risk assessments and individual driver attributions.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `score_id` | `UUID` | No | PK | `gen_random_uuid()` | Prediction batch ID. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Scored employee. |
| `prediction_date` | `DATE` | No | - | - | Date inference was executed. |
| `flight_risk_prob` | `NUMERIC(4, 3)` | No | CHECK (`flight_risk_prob BETWEEN 0.000 AND 1.000`) | - | Model output voluntary attrition probability. |
| `risk_tier` | `risk_tier_enum`| No | - | - | Tier: `'LOW'` (<0.30), `'MEDIUM'` (0.30-0.65), `'HIGH'` (0.65-0.85), `'CRITICAL'` (>0.85). |
| `model_version` | `VARCHAR(32)` | No | - | `'v1.0.0'` | Version tag of trained model artifact. |
| `top_driver_1` | `VARCHAR(100)`| No | - | - | Primary SHAP feature contribution (e.g., `compa_ratio_low`). |
| `driver_1_shap_val`| `NUMERIC(6, 4)` | No | - | - | Shapley value contribution for primary driver. |
| `top_driver_2` | `VARCHAR(100)`| Yes | - | NULL | Secondary SHAP feature contribution. |
| `driver_2_shap_val`| `NUMERIC(6, 4)` | Yes | - | NULL | Shapley value contribution for secondary driver. |
| `top_driver_3` | `VARCHAR(100)`| Yes | - | NULL | Tertiary SHAP feature contribution. |
| `driver_3_shap_val`| `NUMERIC(6, 4)` | Yes | - | NULL | Shapley value contribution for tertiary driver. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Ingestion timestamp. |

- **Cardinality:** One Employee has Many Historical Predictions (`1:N`).

---

### 3.9 Entity 9: `retention_interventions` (Retention Action Lifecycle)
*Orchestrates targeted HR interventions, approval statuses, financial investments, and outcomes.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `intervention_id` | `UUID` | No | PK | `gen_random_uuid()` | Intervention event ID. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`) | - | Target employee. |
| `risk_score_id` | `UUID` | Yes | FK (`attrition_risk_scores.score_id`) | NULL | Triggering flight risk assessment record. |
| `intervention_type` | `intervention_type_enum` | No | - | - | Retention mechanism. |
| `status` | `intervention_status_enum` | No | - | `'RECOMMENDED'`| Lifecycle status. |
| `cost_usd` | `NUMERIC(10, 2)`| No | CHECK (`cost_usd >= 0.00`) | `0.00` | Financial investment required (e.g. bonus, adjustment). |
| `proposed_date` | `DATE` | No | - | - | Date intervention was generated/recommended. |
| `action_date` | `DATE` | Yes | CHECK (`action_date IS NULL OR action_date >= proposed_date`) | NULL | Date presented or executed to employee. |
| `outcome_evaluated_date` | `DATE` | Yes | CHECK (`outcome_evaluated_date IS NULL OR outcome_evaluated_date >= action_date`) | NULL | 90-day/180-day retention evaluation date. |
| `is_successful` | `BOOLEAN` | Yes | - | NULL | Retention result: TRUE if employee remained, FALSE if left. |
| `hr_notes` | `TEXT` | Yes | - | NULL | HRBP comments and execution history. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | Audit timestamp. |

---

### 3.10 Entity 10: `exit_records` (Separation & Attrition Outcomes)
*Records final employee departures, regret status, separation rationale, and exit interview responses.*

| Column Name | Data Type | Nullable | Constraints | Default | Description & Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `exit_id` | `UUID` | No | PK | `gen_random_uuid()` | Exit record identifier. |
| `employee_id` | `VARCHAR(32)` | No | FK (`employees.employee_id`), UNIQUE | - | Offboarded employee. Enforces 1:1 constraint. |
| `separation_date` | `DATE` | No | - | - | Official last day of employment. |
| `separation_type` | `separation_type_enum` | No | - | - | Category (`VOLUNTARY`, `INVOLUNTARY`, etc.). |
| `regret_status` | `regret_status_enum` | No | - | - | Business impact: High performers leaving = `REGRETTABLE`. |
| `primary_reason` | `VARCHAR(100)`| No | - | - | Primary reason (e.g., `'COMPENSATION'`, `'CAREER_ADVANCEMENT'`, `'MANAGEMENT_CONFLICT'`, `'RELOCATION'`). |
| `secondary_reason`| `VARCHAR(100)`| Yes | - | NULL | Secondary contributing factor. |
| `notice_period_days_served` | `INTEGER` | No | CHECK (`notice_period_days_served >= 0`) | `0` | Number of days of contractual notice worked. |
| `exit_interview_completed` | `BOOLEAN` | No | - | `FALSE` | Confirmation of exit survey interview. |
| `would_rehire` | `BOOLEAN` | No | - | `TRUE` | Whether organizational rehire is permissible. |
| `destination_industry` | `VARCHAR(100)`| Yes | - | NULL | Destination sector (e.g. `'Direct Competitor'`, `'Startup'`). |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | - | `CURRENT_TIMESTAMP` | System recording timestamp. |

---

## 4. Supporting & Governance Tables

### 4.1 Tables: `skills` and `employee_skills` (Skills Matrix Bridge)
*Tracks organizational competency taxonomy and employee proficiency.*

#### `skills`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `skill_id` | `VARCHAR(32)` | PK | Unique skill code (e.g., `SKL-PY-01`). |
| `name` | `VARCHAR(100)` | UNIQUE, NOT NULL | Skill name (e.g., `Python Data Engineering`). |
| `category` | `VARCHAR(50)` | NOT NULL | Category (e.g., `Data Science`, `Cloud Architecture`, `Sales`). |

#### `employee_skills` (Bridge)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `employee_id` | `VARCHAR(32)` | FK (`employees.employee_id`), PK | Associated employee. |
| `skill_id` | `VARCHAR(32)` | FK (`skills.skill_id`), PK | Associated skill. |
| `proficiency_level` | `INTEGER` | NOT NULL, CHECK (`proficiency_level BETWEEN 1 AND 5`) | 1=Beginner, 5=Expert. |
| `certified_flag` | `BOOLEAN` | NOT NULL, DEFAULT `FALSE` | Certified accreditation status. |

---

### 4.2 Table: `employee_history` (SCD Type 2 Dimension)
*Tracks every mutation of an employee's title, department, salary grade, and supervisor.*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `history_id` | `UUID` | PK, DEFAULT `gen_random_uuid()` | Snapshot ID. |
| `employee_id` | `VARCHAR(32)` | FK (`employees.employee_id`), NOT NULL | Associated worker. |
| `department_id` | `VARCHAR(32)` | FK (`departments.department_id`), NOT NULL | Historic department. |
| `role_id` | `VARCHAR(32)` | FK (`job_roles.role_id`), NOT NULL | Historic job role. |
| `manager_id` | `VARCHAR(32)` | FK (`employees.employee_id`), NULLABLE | Historic manager. |
| `status` | `employment_status_enum` | NOT NULL | Historic status. |
| `effective_from` | `DATE` | NOT NULL | Start date of this profile state. |
| `effective_to` | `DATE` | NULLABLE, CHECK (`effective_to IS NULL OR effective_to >= effective_from`) | End date. NULL if current. |
| `is_current` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | Quick flag for active record. |
| `change_reason` | `VARCHAR(100)`| NOT NULL | e.g., `'PROMOTION'`, `'DEPARTMENT_TRANSFER'`, `'MANAGER_CHANGE'`. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Transaction write time. |

---

### 4.3 Table: `time_off_records` (Absence & Leave)
*Tracks approved leave periods to cross-validate operational project hours (ANOM-04).*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `leave_id` | `UUID` | PK, DEFAULT `gen_random_uuid()` | Leave record ID. |
| `employee_id` | `VARCHAR(32)` | FK (`employees.employee_id`), NOT NULL | Absent employee. |
| `leave_type` | `leave_type_enum` | NOT NULL | Category of leave. |
| `start_date` | `DATE` | NOT NULL | Leave commencement date. |
| `end_date` | `DATE` | NOT NULL, CHECK (`end_date >= start_date`) | Final date of leave. |
| `is_approved` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | Approval status. |
| `total_days` | `NUMERIC(4, 1)` | NOT NULL, CHECK (`total_days > 0`) | Business days taken. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Audit timestamp. |

---

### 4.4 Table: `data_anomalies` (Exception & Quarantine Table)
*Quarantines detected data integrity violations across the 4 mandatory anomaly scenarios.*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `anomaly_id` | `UUID` | PK, DEFAULT `gen_random_uuid()` | Exception record identifier. |
| `anomaly_type` | `anomaly_type_enum` | NOT NULL | Category of the violation. |
| `severity` | `severity_level_enum`| NOT NULL | Severity level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). |
| `entity_type` | `VARCHAR(50)` | NOT NULL | Affected table (e.g., `'employees'`, `'project_assignments'`). |
| `entity_id` | `VARCHAR(64)` | NOT NULL | Primary key value of the offending record. |
| `description` | `TEXT` | NOT NULL | Human-readable explanation of why the rule failed. |
| `payload_snapshot` | `JSONB` | Yes | Raw record snapshot at time of detection. |
| `detected_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Timestamp when exception was triggered. |
| `is_resolved` | `BOOLEAN` | NOT NULL, DEFAULT `FALSE` | Resolution workflow flag. |
| `resolved_by` | `VARCHAR(50)` | Yes | User ID or process that resolved the anomaly. |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Yes | Timestamp of resolution. |

---

### 4.5 Table: `audit_logs` (System Mutation Ledger)
*Immutable audit trail capturing all DDL/DML events, user interactions, and modifications.*

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `log_id` | `BIGSERIAL` | PK | Monotonically increasing event ID. |
| `table_name` | `VARCHAR(50)` | NOT NULL | Target table modified. |
| `record_id` | `VARCHAR(64)` | NOT NULL | Primary key of modified row. |
| `action` | `VARCHAR(10)` | NOT NULL, CHECK (`action IN ('INSERT', 'UPDATE', 'DELETE')`) | Mutation type. |
| `old_values` | `JSONB` | Yes | Pre-mutation JSON snapshot. NULL on INSERT. |
| `new_values` | `JSONB` | Yes | Post-mutation JSON snapshot. NULL on DELETE. |
| `actor_id` | `VARCHAR(50)` | NOT NULL | User or service triggering the event. |
| `client_ip` | `VARCHAR(45)` | Yes | IP address of caller. |
| `recorded_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Exact transaction commit timestamp. |
