"""
SQLAlchemy ORM models mirroring the WorkforceIQ schema (database/schema.sql).
All enum types, constraints and relationships are preserved from Phase 1.
"""

import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime,
    ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


# ---------------------------------------------------------------------------
# Python Enum mirrors of PostgreSQL enum types
# ---------------------------------------------------------------------------

class EmploymentStatusEnum(str, enum.Enum):
    APPLICANT = "APPLICANT"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    NOTICE_PERIOD = "NOTICE_PERIOD"
    TERMINATED = "TERMINATED"
    RETIRED = "RETIRED"

class EmploymentTypeEnum(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACTOR = "CONTRACTOR"
    INTERN = "INTERN"

class WorkLocationEnum(str, enum.Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"

class SeparationTypeEnum(str, enum.Enum):
    VOLUNTARY = "VOLUNTARY"
    INVOLUNTARY = "INVOLUNTARY"
    RETIREMENT = "RETIREMENT"
    CONTRACT_END = "CONTRACT_END"

class RegretStatusEnum(str, enum.Enum):
    REGRETTABLE = "REGRETTABLE"
    NON_REGRETTABLE = "NON_REGRETTABLE"
    UNDETERMINED = "UNDETERMINED"

class RiskTierEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class InterventionTypeEnum(str, enum.Enum):
    COMPENSATION_INCREASE = "COMPENSATION_INCREASE"
    RETENTION_BONUS = "RETENTION_BONUS"
    ROLE_PROMOTION = "ROLE_PROMOTION"
    PROJECT_REASSIGNMENT = "PROJECT_REASSIGNMENT"
    FLEXIBLE_WORK_SCHEDULE = "FLEXIBLE_WORK_SCHEDULE"
    EXECUTIVE_MENTORSHIP = "EXECUTIVE_MENTORSHIP"
    CAREER_DEVELOPMENT = "CAREER_DEVELOPMENT"

class InterventionStatusEnum(str, enum.Enum):
    # Phase 5 lifecycle (maps to challenge statuses):
    CREATED = "CREATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    # Keep legacy statuses from generator for backwards compatibility
    RECOMMENDED = "RECOMMENDED"
    REJECTED = "REJECTED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    FAILED = "FAILED"

class ReviewRatingEnum(str, enum.Enum):
    UNSATISFACTORY = "UNSATISFACTORY"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    MEETS_EXPECTATIONS = "MEETS_EXPECTATIONS"
    EXCEEDS_EXPECTATIONS = "EXCEEDS_EXPECTATIONS"
    OUTSTANDING = "OUTSTANDING"

class AnomalyTypeEnum(str, enum.Enum):
    POST_TERMINATION_ACTIVITY = "POST_TERMINATION_ACTIVITY"
    CIRCULAR_HIERARCHY = "CIRCULAR_HIERARCHY"
    COMPENSATION_INVERSION = "COMPENSATION_INVERSION"
    LEAVE_HOUR_CONFLICT = "LEAVE_HOUR_CONFLICT"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    DATA_LEAKAGE = "DATA_LEAKAGE"

class SeverityLevelEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class LeaveTypeEnum(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    BEREAVEMENT = "BEREAVEMENT"
    UNPAID = "UNPAID"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Department(Base):
    __tablename__ = "departments"

    department_id = Column(String(32), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    division = Column(String(100), nullable=False)
    cost_center_code = Column(String(32), nullable=False, unique=True)
    head_employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True)
    parent_department_id = Column(String(32), ForeignKey("departments.department_id", ondelete="RESTRICT"), nullable=True)
    annual_budget = Column(Numeric(14, 2), nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    roles = relationship("JobRole", back_populates="department")


class JobRole(Base):
    __tablename__ = "job_roles"
    __table_args__ = (
        UniqueConstraint("department_id", "title", "grade_level", name="uq_dept_role_grade"),
    )

    role_id = Column(String(32), primary_key=True)
    department_id = Column(String(32), ForeignKey("departments.department_id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(100), nullable=False)
    grade_level = Column(Integer, nullable=False)
    min_salary = Column(Numeric(12, 2), nullable=False)
    mid_salary = Column(Numeric(12, 2), nullable=False)
    max_salary = Column(Numeric(12, 2), nullable=False)
    is_exempt = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    department = relationship("Department", back_populates="roles")
    employees = relationship("Employee", back_populates="role")


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String(32), primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    department_id = Column(String(32), ForeignKey("departments.department_id", ondelete="RESTRICT"), nullable=False)
    role_id = Column(String(32), ForeignKey("job_roles.role_id", ondelete="RESTRICT"), nullable=False)
    manager_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="RESTRICT"), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    employment_type = Column(String(20), nullable=False, default="FULL_TIME")
    work_location = Column(String(20), nullable=False, default="HYBRID")
    hire_date = Column(Date, nullable=False)
    probation_end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    role = relationship("JobRole", back_populates="employees")
    manager = relationship("Employee", remote_side="Employee.employee_id", foreign_keys=[manager_id])
    compensation_records = relationship("CompensationRecord", back_populates="employee", cascade="all, delete-orphan")
    performance_evaluations = relationship("PerformanceEvaluation", back_populates="employee",
                                           foreign_keys="PerformanceEvaluation.employee_id", cascade="all, delete-orphan")
    engagement_surveys = relationship("EngagementSurvey", back_populates="employee", cascade="all, delete-orphan")
    project_assignments = relationship("ProjectAssignment", back_populates="employee", cascade="all, delete-orphan")
    time_off_records = relationship("TimeOffRecord", back_populates="employee", cascade="all, delete-orphan")
    attrition_risk_scores = relationship("AttritionRiskScore", back_populates="employee", cascade="all, delete-orphan")
    interventions = relationship("RetentionIntervention", back_populates="employee", cascade="all, delete-orphan")
    exit_record = relationship("ExitRecord", back_populates="employee", uselist=False, cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(32), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(String(32), ForeignKey("skills.skill_id", ondelete="RESTRICT"), primary_key=True)
    proficiency_level = Column(Integer, nullable=False)
    certified_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmployeeHistory(Base):
    __tablename__ = "employee_history"

    history_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String(32), ForeignKey("departments.department_id", ondelete="RESTRICT"), nullable=False)
    role_id = Column(String(32), ForeignKey("job_roles.role_id", ondelete="RESTRICT"), nullable=False)
    manager_id = Column(String(32), nullable=True)
    status = Column(String(20), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)
    change_reason = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CompensationRecord(Base):
    __tablename__ = "compensation_records"

    compensation_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    base_salary = Column(Numeric(12, 2), nullable=False)
    bonus_target_pct = Column(Numeric(5, 2), nullable=False, default=0.0)
    stock_options_granted = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)
    revision_reason = Column(String(100), nullable=False, default="ANNUAL_REVIEW")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="compensation_records")


class PerformanceEvaluation(Base):
    __tablename__ = "performance_evaluations"
    __table_args__ = (
        UniqueConstraint("employee_id", "evaluation_cycle", name="uq_emp_eval_cycle"),
    )

    evaluation_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="RESTRICT"), nullable=False)
    evaluation_cycle = Column(String(32), nullable=False)
    rating = Column(String(30), nullable=False)
    numeric_score = Column(Numeric(3, 2), nullable=False)
    goals_met_pct = Column(Numeric(5, 2), nullable=False)
    promotion_readiness = Column(String(32), nullable=False, default="DEVELOPING")
    feedback_summary = Column(Text, nullable=True)
    evaluation_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="performance_evaluations", foreign_keys=[employee_id])


class EngagementSurvey(Base):
    __tablename__ = "engagement_surveys"
    __table_args__ = (
        UniqueConstraint("employee_id", "survey_date", name="uq_emp_survey_date"),
    )

    survey_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    survey_date = Column(Date, nullable=False)
    enps_score = Column(Integer, nullable=False)
    job_satisfaction = Column(Integer, nullable=False)
    work_life_balance = Column(Integer, nullable=False)
    management_trust = Column(Integer, nullable=False)
    career_growth_opps = Column(Integer, nullable=False)
    burnout_risk_index = Column(Numeric(3, 2), nullable=False)
    sentiment_score = Column(Numeric(3, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="engagement_surveys")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String(32), primary_key=True)
    department_id = Column(String(32), ForeignKey("departments.department_id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_billable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    assignments = relationship("ProjectAssignment", back_populates="project")


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"

    assignment_id = Column(String(64), primary_key=True)
    project_id = Column(String(32), ForeignKey("projects.project_id", ondelete="RESTRICT"), nullable=False)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    role_in_project = Column(String(50), nullable=False, default="CONTRIBUTOR")
    allocation_pct = Column(Integer, nullable=False, default=100)
    logged_hours_weekly = Column(Numeric(5, 2), nullable=False, default=40.0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="project_assignments")
    project = relationship("Project", back_populates="assignments")


class TimeOffRecord(Base):
    __tablename__ = "time_off_records"

    leave_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    leave_type = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_approved = Column(Boolean, nullable=False, default=True)
    total_days = Column(Numeric(4, 1), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="time_off_records")


class AttritionRiskScore(Base):
    __tablename__ = "attrition_risk_scores"
    __table_args__ = (
        UniqueConstraint("employee_id", "prediction_date", name="uq_emp_pred_date"),
    )

    score_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    prediction_date = Column(Date, nullable=False)
    flight_risk_prob = Column(Numeric(4, 3), nullable=False)
    risk_tier = Column(String(20), nullable=False)
    model_version = Column(String(32), nullable=False, default="v1.0.0")
    top_driver_1 = Column(String(100), nullable=False)
    driver_1_shap_val = Column(Numeric(6, 4), nullable=False)
    top_driver_2 = Column(String(100), nullable=True)
    driver_2_shap_val = Column(Numeric(6, 4), nullable=True)
    top_driver_3 = Column(String(100), nullable=True)
    driver_3_shap_val = Column(Numeric(6, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="attrition_risk_scores")
    interventions = relationship("RetentionIntervention", back_populates="risk_score")


class RetentionIntervention(Base):
    __tablename__ = "retention_interventions"

    intervention_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    risk_score_id = Column(String(64), ForeignKey("attrition_risk_scores.score_id", ondelete="SET NULL"), nullable=True)
    intervention_type = Column(String(40), nullable=False)
    status = Column(String(30), nullable=False, default="CREATED")
    cost_usd = Column(Numeric(10, 2), nullable=False, default=0.0)
    proposed_date = Column(Date, nullable=False)
    action_date = Column(Date, nullable=True)
    outcome_evaluated_date = Column(Date, nullable=True)
    is_successful = Column(Boolean, nullable=True)
    hr_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee", back_populates="interventions")
    risk_score = relationship("AttritionRiskScore", back_populates="interventions")
    events = relationship("InterventionEvent", back_populates="intervention", cascade="all, delete-orphan")


class InterventionEvent(Base):
    """Immutable audit trail of every intervention status change."""
    __tablename__ = "intervention_events"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    intervention_id = Column(String(64), ForeignKey("retention_interventions.intervention_id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    actor = Column(String(100), nullable=False, default="SYSTEM")
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    intervention = relationship("RetentionIntervention", back_populates="events")


class ExitRecord(Base):
    __tablename__ = "exit_records"

    exit_id = Column(String(64), primary_key=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False, unique=True)
    separation_date = Column(Date, nullable=False)
    separation_type = Column(String(20), nullable=False)
    regret_status = Column(String(30), nullable=False)
    primary_reason = Column(String(100), nullable=False)
    secondary_reason = Column(String(100), nullable=True)
    notice_period_days_served = Column(Integer, nullable=False, default=0)
    exit_interview_completed = Column(Boolean, nullable=False, default=False)
    would_rehire = Column(Boolean, nullable=False, default=True)
    destination_industry = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="exit_record")


class DataAnomaly(Base):
    __tablename__ = "data_anomalies"

    anomaly_id = Column(String(64), primary_key=True)
    anomaly_type = Column(String(40), nullable=False)
    severity = Column(String(20), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    payload_snapshot = Column(JSON, nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(64), nullable=False)
    action = Column(String(10), nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    actor_id = Column(String(50), nullable=False, default="SYSTEM")
    client_ip = Column(String(45), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
