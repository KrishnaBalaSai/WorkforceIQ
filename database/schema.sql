-- ============================================================================
-- Workforce Retention Intelligence Platform (WorkforceIQ)
-- Database Schema DDL Specification (PostgreSQL / ANSI SQL Compatible)
-- Version: 1.0.0
-- Phase: Phase 1 Design Baseline
-- ============================================================================

-- Enable UUID extension for high-performance random UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. ENUMERATED TYPES (DOMAIN RESTRICTIONS)
-- ============================================================================

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employment_status_enum') THEN
        CREATE TYPE employment_status_enum AS ENUM (
            'APPLICANT', 'ONBOARDING', 'ACTIVE', 'ON_LEAVE', 'NOTICE_PERIOD', 'TERMINATED', 'RETIRED'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employment_type_enum') THEN
        CREATE TYPE employment_type_enum AS ENUM (
            'FULL_TIME', 'PART_TIME', 'CONTRACTOR', 'INTERN'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'work_location_enum') THEN
        CREATE TYPE work_location_enum AS ENUM (
            'ONSITE', 'HYBRID', 'REMOTE'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'separation_type_enum') THEN
        CREATE TYPE separation_type_enum AS ENUM (
            'VOLUNTARY', 'INVOLUNTARY', 'RETIREMENT', 'CONTRACT_END'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'regret_status_enum') THEN
        CREATE TYPE regret_status_enum AS ENUM (
            'REGRETTABLE', 'NON_REGRETTABLE', 'UNDETERMINED'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'risk_tier_enum') THEN
        CREATE TYPE risk_tier_enum AS ENUM (
            'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'intervention_type_enum') THEN
        CREATE TYPE intervention_type_enum AS ENUM (
            'COMPENSATION_INCREASE', 'RETENTION_BONUS', 'ROLE_PROMOTION', 
            'PROJECT_REASSIGNMENT', 'FLEXIBLE_WORK_SCHEDULE', 'EXECUTIVE_MENTORSHIP', 
            'CAREER_DEVELOPMENT'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'intervention_status_enum') THEN
        CREATE TYPE intervention_status_enum AS ENUM (
            'RECOMMENDED', 'APPROVED', 'REJECTED', 'OFFERED', 'ACCEPTED', 'DECLINED', 'COMPLETED', 'FAILED'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_rating_enum') THEN
        CREATE TYPE review_rating_enum AS ENUM (
            'UNSATISFACTORY', 'NEEDS_IMPROVEMENT', 'MEETS_EXPECTATIONS', 'EXCEEDS_EXPECTATIONS', 'OUTSTANDING'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'anomaly_type_enum') THEN
        CREATE TYPE anomaly_type_enum AS ENUM (
            'POST_TERMINATION_ACTIVITY', 'CIRCULAR_HIERARCHY', 'COMPENSATION_INVERSION', 
            'LEAVE_HOUR_CONFLICT', 'SCHEMA_VIOLATION', 'DATA_LEAKAGE'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'severity_level_enum') THEN
        CREATE TYPE severity_level_enum AS ENUM (
            'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leave_type_enum') THEN
        CREATE TYPE leave_type_enum AS ENUM (
            'ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'BEREAVEMENT', 'UNPAID'
        );
    END IF;
END $$;

-- ============================================================================
-- 2. CORE & SUPPORTING RELATIONAL ENTITIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Entity 1: departments
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    department_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    division VARCHAR(100) NOT NULL,
    cost_center_code VARCHAR(32) NOT NULL UNIQUE,
    head_employee_id VARCHAR(32), -- FK added after employees table creation
    parent_department_id VARCHAR(32) REFERENCES departments(department_id) ON DELETE RESTRICT,
    annual_budget NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (annual_budget >= 0.00),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE departments IS 'Cost centers, business units, and organizational hierarchies.';
COMMENT ON COLUMN departments.annual_budget IS 'Allocated annual operational budget in USD.';

-- ----------------------------------------------------------------------------
-- Entity 2: job_roles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_roles (
    role_id VARCHAR(32) PRIMARY KEY,
    department_id VARCHAR(32) NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    title VARCHAR(100) NOT NULL,
    grade_level INTEGER NOT NULL CHECK (grade_level BETWEEN 1 AND 15),
    min_salary NUMERIC(12, 2) NOT NULL CHECK (min_salary >= 0.00),
    mid_salary NUMERIC(12, 2) NOT NULL CHECK (mid_salary >= min_salary),
    max_salary NUMERIC(12, 2) NOT NULL CHECK (max_salary >= mid_salary),
    is_exempt BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dept_role_grade UNIQUE (department_id, title, grade_level)
);

COMMENT ON TABLE job_roles IS 'Standardized job catalog, grade seniority tiers, and compensation bands.';
COMMENT ON COLUMN job_roles.mid_salary IS 'Benchmark midpoint salary for compa-ratio computations.';

-- ----------------------------------------------------------------------------
-- Entity 3: employees
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id VARCHAR(32) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department_id VARCHAR(32) NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    role_id VARCHAR(32) NOT NULL REFERENCES job_roles(role_id) ON DELETE RESTRICT,
    manager_id VARCHAR(32) REFERENCES employees(employee_id) ON DELETE RESTRICT,
    status employment_status_enum NOT NULL DEFAULT 'ACTIVE',
    employment_type employment_type_enum NOT NULL DEFAULT 'FULL_TIME',
    work_location work_location_enum NOT NULL DEFAULT 'HYBRID',
    hire_date DATE NOT NULL,
    probation_end_date DATE CHECK (probation_end_date IS NULL OR probation_end_date >= hire_date),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE employees IS 'Master worker profile and organizational reporting graph node.';

-- Establish mutual circular foreign key from departments to department head
ALTER TABLE departments 
    DROP CONSTRAINT IF EXISTS fk_departments_head;
ALTER TABLE departments 
    ADD CONSTRAINT fk_departments_head 
    FOREIGN KEY (head_employee_id) REFERENCES employees(employee_id) ON DELETE SET NULL;

-- ----------------------------------------------------------------------------
-- Supporting: skills & employee_skills (Bridge)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    skill_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employee_skills (
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    skill_id VARCHAR(32) NOT NULL REFERENCES skills(skill_id) ON DELETE RESTRICT,
    proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    certified_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id, skill_id)
);

-- ----------------------------------------------------------------------------
-- Supporting: employee_history (SCD Type 2 Historical Ledger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employee_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    department_id VARCHAR(32) NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    role_id VARCHAR(32) NOT NULL REFERENCES job_roles(role_id) ON DELETE RESTRICT,
    manager_id VARCHAR(32) REFERENCES employees(employee_id) ON DELETE SET NULL,
    status employment_status_enum NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE CHECK (effective_to IS NULL OR effective_to >= effective_from),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    change_reason VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_emp_hist_active_single 
    ON employee_history (employee_id) 
    WHERE is_current = TRUE;

COMMENT ON TABLE employee_history IS 'Slowly Changing Dimension Type 2 (SCD2) history for employee movements.';

-- ----------------------------------------------------------------------------
-- Entity 4: compensation_records (Total Rewards History)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compensation_records (
    compensation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    base_salary NUMERIC(12, 2) NOT NULL CHECK (base_salary > 0.00),
    bonus_target_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (bonus_target_pct BETWEEN 0.00 AND 100.00),
    stock_options_granted INTEGER NOT NULL DEFAULT 0 CHECK (stock_options_granted >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3),
    effective_from DATE NOT NULL,
    effective_to DATE CHECK (effective_to IS NULL OR effective_to >= effective_from),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    revision_reason VARCHAR(100) NOT NULL DEFAULT 'ANNUAL_REVIEW',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_comp_active_single 
    ON compensation_records (employee_id) 
    WHERE is_current = TRUE;

COMMENT ON TABLE compensation_records IS 'Longitudinal employee compensation and equity grants.';

-- ----------------------------------------------------------------------------
-- Entity 5: performance_evaluations (Talent Appraisals)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    reviewer_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE RESTRICT,
    evaluation_cycle VARCHAR(32) NOT NULL,
    rating review_rating_enum NOT NULL,
    numeric_score NUMERIC(3, 2) NOT NULL CHECK (numeric_score BETWEEN 1.00 AND 5.00),
    goals_met_pct NUMERIC(5, 2) NOT NULL CHECK (goals_met_pct BETWEEN 0.00 AND 150.00),
    promotion_readiness VARCHAR(32) NOT NULL DEFAULT 'DEVELOPING' 
        CHECK (promotion_readiness IN ('NOT_READY', 'DEVELOPING', 'READY_NOW', 'PROMOTED')),
    feedback_summary TEXT,
    evaluation_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_emp_eval_cycle UNIQUE (employee_id, evaluation_cycle)
);

COMMENT ON TABLE performance_evaluations IS 'Periodic formal appraisals, scores, and promotion readiness.';

-- ----------------------------------------------------------------------------
-- Entity 6: engagement_surveys (Pulse & Sentiment)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS engagement_surveys (
    survey_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    survey_date DATE NOT NULL,
    enps_score INTEGER NOT NULL CHECK (enps_score BETWEEN 0 AND 10),
    job_satisfaction INTEGER NOT NULL CHECK (job_satisfaction BETWEEN 1 AND 5),
    work_life_balance INTEGER NOT NULL CHECK (work_life_balance BETWEEN 1 AND 5),
    management_trust INTEGER NOT NULL CHECK (management_trust BETWEEN 1 AND 5),
    career_growth_opps INTEGER NOT NULL CHECK (career_growth_opps BETWEEN 1 AND 5),
    burnout_risk_index NUMERIC(3, 2) NOT NULL CHECK (burnout_risk_index BETWEEN 0.00 AND 1.00),
    sentiment_score NUMERIC(3, 2) NOT NULL CHECK (sentiment_score BETWEEN -1.00 AND 1.00),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_emp_survey_date UNIQUE (employee_id, survey_date)
);

COMMENT ON TABLE engagement_surveys IS 'Periodic sentiment surveys, eNPS, and burnout assessments.';

-- ----------------------------------------------------------------------------
-- Entity 7: projects & project_assignments (Operations)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR(32) PRIMARY KEY,
    department_id VARCHAR(32) NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    start_date DATE NOT NULL,
    end_date DATE CHECK (end_date IS NULL OR end_date >= start_date),
    is_billable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id VARCHAR(32) NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    role_in_project VARCHAR(50) NOT NULL DEFAULT 'CONTRIBUTOR',
    allocation_pct INTEGER NOT NULL DEFAULT 100 CHECK (allocation_pct BETWEEN 1 AND 100),
    logged_hours_weekly NUMERIC(5, 2) NOT NULL DEFAULT 40.00 CHECK (logged_hours_weekly >= 0.00),
    start_date DATE NOT NULL,
    end_date DATE CHECK (end_date IS NULL OR end_date >= start_date),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_emp_proj_start UNIQUE (employee_id, project_id, start_date)
);

COMMENT ON TABLE project_assignments IS 'Employee project allocation and billable work logging.';

-- ----------------------------------------------------------------------------
-- Supporting: time_off_records (Absence & Leave)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS time_off_records (
    leave_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    leave_type leave_type_enum NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL CHECK (end_date >= start_date),
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    total_days NUMERIC(4, 1) NOT NULL CHECK (total_days > 0.0),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE time_off_records IS 'Approved employee leaves used to cross-verify operational logging.';

-- ----------------------------------------------------------------------------
-- Entity 8: attrition_risk_scores (Predictive Flight Risk)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attrition_risk_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    prediction_date DATE NOT NULL,
    flight_risk_prob NUMERIC(4, 3) NOT NULL CHECK (flight_risk_prob BETWEEN 0.000 AND 1.000),
    risk_tier risk_tier_enum NOT NULL,
    model_version VARCHAR(32) NOT NULL DEFAULT 'v1.0.0',
    top_driver_1 VARCHAR(100) NOT NULL,
    driver_1_shap_val NUMERIC(6, 4) NOT NULL,
    top_driver_2 VARCHAR(100),
    driver_2_shap_val NUMERIC(6, 4),
    top_driver_3 VARCHAR(100),
    driver_3_shap_val NUMERIC(6, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_emp_pred_date UNIQUE (employee_id, prediction_date)
);

COMMENT ON TABLE attrition_risk_scores IS 'Historical machine learning flight risk predictions and SHAP attributions.';

-- ----------------------------------------------------------------------------
-- Entity 9: retention_interventions (Retention Action Lifecycle)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS retention_interventions (
    intervention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    risk_score_id UUID REFERENCES attrition_risk_scores(score_id) ON DELETE SET NULL,
    intervention_type intervention_type_enum NOT NULL,
    status intervention_status_enum NOT NULL DEFAULT 'RECOMMENDED',
    cost_usd NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (cost_usd >= 0.00),
    proposed_date DATE NOT NULL,
    action_date DATE CHECK (action_date IS NULL OR action_date >= proposed_date),
    outcome_evaluated_date DATE CHECK (outcome_evaluated_date IS NULL OR outcome_evaluated_date >= action_date),
    is_successful BOOLEAN,
    hr_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE retention_interventions IS 'Workflow management for proactive talent retention actions.';

-- ----------------------------------------------------------------------------
-- Entity 10: exit_records (Separation & Attrition Outcomes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exit_records (
    exit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(32) NOT NULL UNIQUE REFERENCES employees(employee_id) ON DELETE CASCADE,
    separation_date DATE NOT NULL,
    separation_type separation_type_enum NOT NULL,
    regret_status regret_status_enum NOT NULL,
    primary_reason VARCHAR(100) NOT NULL,
    secondary_reason VARCHAR(100),
    notice_period_days_served INTEGER NOT NULL DEFAULT 0 CHECK (notice_period_days_served >= 0),
    exit_interview_completed BOOLEAN NOT NULL DEFAULT FALSE,
    would_rehire BOOLEAN NOT NULL DEFAULT TRUE,
    destination_industry VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE exit_records IS 'Official terminal offboarding records and exit survey analysis.';

-- ----------------------------------------------------------------------------
-- Governance: data_anomalies (Quarantine & Exception Queue)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_type anomaly_type_enum NOT NULL,
    severity severity_level_enum NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    payload_snapshot JSONB,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE data_anomalies IS 'Centralized quarantine and exception queue for data integrity failures.';

-- ----------------------------------------------------------------------------
-- Governance: audit_logs (System Ledger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id VARCHAR(64) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    actor_id VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    client_ip VARCHAR(45),
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE audit_logs IS 'Immutable append-only audit trail capturing database mutations.';

-- ============================================================================
-- 3. INDEXES FOR QUERY OPTIMIZATION
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role_id);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status, is_active);

CREATE INDEX IF NOT EXISTS idx_comp_emp ON compensation_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_eval_emp ON performance_evaluations(employee_id);
CREATE INDEX IF NOT EXISTS idx_eval_reviewer ON performance_evaluations(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_survey_emp ON engagement_surveys(employee_id);
CREATE INDEX IF NOT EXISTS idx_assignment_emp ON project_assignments(employee_id);
CREATE INDEX IF NOT EXISTS idx_assignment_proj ON project_assignments(project_id);
CREATE INDEX IF NOT EXISTS idx_time_off_emp ON time_off_records(employee_id);

CREATE INDEX IF NOT EXISTS idx_risk_emp_date ON attrition_risk_scores(employee_id, prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_risk_tier ON attrition_risk_scores(risk_tier);
CREATE INDEX IF NOT EXISTS idx_intervention_emp ON retention_interventions(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_exit_date ON exit_records(separation_date);
CREATE INDEX IF NOT EXISTS idx_anomalies_resolved ON data_anomalies(is_resolved, severity);

-- ============================================================================
-- 4. AUTOMATED TIMESTAMP TRIGGER FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dept_updated_at ON departments;
CREATE TRIGGER trg_dept_updated_at
    BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

DROP TRIGGER IF EXISTS trg_roles_updated_at ON job_roles;
CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON job_roles
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

DROP TRIGGER IF EXISTS trg_emp_updated_at ON employees;
CREATE TRIGGER trg_emp_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

DROP TRIGGER IF EXISTS trg_intervention_updated_at ON retention_interventions;
CREATE TRIGGER trg_intervention_updated_at
    BEFORE UPDATE ON retention_interventions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- ============================================================================
-- 5. ANALYTICAL VIEWS
-- ============================================================================

-- View 1: Active Employee 360 View
CREATE OR REPLACE VIEW v_employee_360 AS
SELECT 
    e.employee_id,
    e.first_name,
    e.last_name,
    e.email,
    e.status,
    e.employment_type,
    e.work_location,
    e.hire_date,
    d.department_id,
    d.name AS department_name,
    d.division,
    r.role_id,
    r.title AS role_title,
    r.grade_level,
    r.min_salary,
    r.mid_salary,
    r.max_salary,
    m.employee_id AS manager_id,
    CONCAT(m.first_name, ' ', m.last_name) AS manager_name,
    c.base_salary,
    c.bonus_target_pct,
    ROUND((c.base_salary / NULLIF(r.mid_salary, 0)), 3) AS compa_ratio,
    pe.rating AS latest_performance_rating,
    pe.numeric_score AS latest_performance_score,
    es.enps_score AS latest_enps_score,
    es.burnout_risk_index AS latest_burnout_risk,
    ars.flight_risk_prob AS latest_flight_risk_prob,
    ars.risk_tier AS latest_risk_tier,
    ars.top_driver_1,
    ars.driver_1_shap_val
FROM employees e
JOIN departments d ON e.department_id = d.department_id
JOIN job_roles r ON e.role_id = r.role_id
LEFT JOIN employees m ON e.manager_id = m.employee_id
LEFT JOIN compensation_records c ON e.employee_id = c.employee_id AND c.is_current = TRUE
LEFT JOIN LATERAL (
    SELECT rating, numeric_score 
    FROM performance_evaluations 
    WHERE employee_id = e.employee_id 
    ORDER BY evaluation_date DESC LIMIT 1
) pe ON TRUE
LEFT JOIN LATERAL (
    SELECT enps_score, burnout_risk_index 
    FROM engagement_surveys 
    WHERE employee_id = e.employee_id 
    ORDER BY survey_date DESC LIMIT 1
) es ON TRUE
LEFT JOIN LATERAL (
    SELECT flight_risk_prob, risk_tier, top_driver_1, driver_1_shap_val 
    FROM attrition_risk_scores 
    WHERE employee_id = e.employee_id 
    ORDER BY prediction_date DESC LIMIT 1
) ars ON TRUE
WHERE e.is_active = TRUE;

-- View 2: High-Risk Retention Watchlist View
CREATE OR REPLACE VIEW v_high_risk_retention_watchlist AS
SELECT 
    v.employee_id,
    CONCAT(v.first_name, ' ', v.last_name) AS employee_name,
    v.department_name,
    v.role_title,
    v.manager_name,
    v.compa_ratio,
    v.latest_flight_risk_prob,
    v.latest_risk_tier,
    v.top_driver_1,
    v.driver_1_shap_val,
    ri.intervention_id,
    ri.intervention_type,
    ri.status AS intervention_status,
    ri.cost_usd
FROM v_employee_360 v
LEFT JOIN LATERAL (
    SELECT intervention_id, intervention_type, status, cost_usd
    FROM retention_interventions
    WHERE employee_id = v.employee_id
      AND status NOT IN ('COMPLETED', 'FAILED', 'REJECTED')
    ORDER BY proposed_date DESC LIMIT 1
) ri ON TRUE
WHERE v.latest_risk_tier IN ('HIGH', 'CRITICAL');

-- View 3: Anomaly 1 Verification - Post-Termination Activity
CREATE OR REPLACE VIEW v_anomaly_post_termination_activity AS
SELECT 
    e.employee_id,
    e.status,
    ex.separation_date,
    'PROJECT_ASSIGNMENT' AS event_source,
    pa.assignment_id::text AS event_id,
    pa.start_date AS activity_date
FROM employees e
JOIN exit_records ex ON e.employee_id = ex.employee_id
JOIN project_assignments pa ON e.employee_id = pa.employee_id
WHERE pa.start_date > ex.separation_date
UNION ALL
SELECT 
    e.employee_id,
    e.status,
    ex.separation_date,
    'ENGAGEMENT_SURVEY' AS event_source,
    es.survey_id::text AS event_id,
    es.survey_date AS activity_date
FROM employees e
JOIN exit_records ex ON e.employee_id = ex.employee_id
JOIN engagement_surveys es ON e.employee_id = es.employee_id
WHERE es.survey_date > ex.separation_date;

-- View 4: Anomaly 2 Verification - Circular Management Hierarchy
CREATE OR REPLACE VIEW v_anomaly_circular_hierarchy AS
WITH RECURSIVE HierarchyCTE AS (
    SELECT 
        employee_id, 
        manager_id, 
        ARRAY[employee_id::text] AS path, 
        FALSE AS is_cycle
    FROM employees
    WHERE manager_id IS NOT NULL
    UNION ALL
    SELECT 
        e.employee_id, 
        e.manager_id, 
        h.path || e.employee_id::text, 
        e.employee_id::text = ANY(h.path)
    FROM employees e
    JOIN HierarchyCTE h ON e.manager_id = h.employee_id
    WHERE NOT h.is_cycle
)
SELECT DISTINCT employee_id, manager_id, path
FROM HierarchyCTE 
WHERE is_cycle = TRUE;

-- View 5: Anomaly 3 Verification - Salary Band Breach
CREATE OR REPLACE VIEW v_anomaly_salary_band_breach AS
SELECT 
    c.compensation_id,
    c.employee_id,
    c.base_salary,
    r.role_id,
    r.title AS role_title,
    r.grade_level,
    r.min_salary,
    r.max_salary,
    CASE 
        WHEN c.base_salary < r.min_salary THEN 'BELOW_MINIMUM'
        WHEN c.base_salary > r.max_salary THEN 'ABOVE_MAXIMUM'
    END AS breach_type,
    CASE 
        WHEN c.base_salary < r.min_salary THEN (r.min_salary - c.base_salary)
        WHEN c.base_salary > r.max_salary THEN (c.base_salary - r.max_salary)
    END AS breach_amount
FROM compensation_records c
JOIN employees e ON c.employee_id = e.employee_id
JOIN job_roles r ON e.role_id = r.role_id
WHERE c.is_current = TRUE
  AND (c.base_salary < r.min_salary OR c.base_salary > r.max_salary);

-- View 6: Anomaly 4 Verification - Leave & Billable Project Conflict
CREATE OR REPLACE VIEW v_anomaly_leave_hour_conflict AS
SELECT 
    pa.assignment_id,
    pa.employee_id,
    pa.project_id,
    pa.logged_hours_weekly,
    t.leave_id,
    t.leave_type,
    t.start_date AS leave_start_date,
    t.end_date AS leave_end_date
FROM project_assignments pa
JOIN time_off_records t ON pa.employee_id = t.employee_id
WHERE t.is_approved = TRUE
  AND (pa.start_date <= t.end_date AND COALESCE(pa.end_date, '9999-12-31') >= t.start_date)
  AND pa.logged_hours_weekly > 0.00;
