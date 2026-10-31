"""
WorkforceIQ Employee Service Layer.
Provides optimized querying, filtering, sorting, pagination, and Employee 360 profiling.
"""

from typing import Optional, Tuple
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.models.orm import (
    AttritionRiskScore,
    CompensationRecord,
    Department,
    Employee,
    EmployeeSkill,
    EngagementSurvey,
    JobRole,
    PerformanceEvaluation,
    ProjectAssignment,
    Skill,
    TimeOffRecord,
)
from backend.schemas.common import PaginatedResponse
from backend.schemas.employees import (
    CompensationItem,
    DepartmentMini,
    EmployeeDetail,
    EmployeeSummary,
    EngagementItem,
    ManagerMini,
    PerformanceItem,
    ProjectAssignmentItem,
    RoleMini,
    SkillItem,
    TimeOffItem,
)


def get_employees(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    department_id: Optional[str] = None,
    role_id: Optional[str] = None,
    status: Optional[str] = None,
    work_location: Optional[str] = None,
    search: Optional[str] = None,
    risk_tier: Optional[str] = None,
    min_risk_probability: Optional[float] = None,
    max_risk_probability: Optional[float] = None,
    sort_by: str = "employee_id",
    sort_order: str = "asc",
) -> PaginatedResponse[EmployeeSummary]:
    """
    Retrieves paginated, filtered, and sorted employee summaries.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    if (
        min_risk_probability is not None
        and max_risk_probability is not None
        and min_risk_probability > max_risk_probability
    ):
        raise ValueError(
            "Minimum risk probability cannot exceed maximum risk probability."
        )

    # Subquery to find the latest prediction date for each employee
    latest_score_subq = (
        select(
            AttritionRiskScore.employee_id,
            func.max(AttritionRiskScore.prediction_date).label("max_pred_date"),
        )
        .group_by(AttritionRiskScore.employee_id)
        .subquery()
    )

    # Join the subquery back to AttritionRiskScore to fetch latest risk details
    latest_risk_subq = (
        select(
            AttritionRiskScore.employee_id,
            AttritionRiskScore.flight_risk_prob,
            AttritionRiskScore.risk_tier,
        )
        .join(
            latest_score_subq,
            (AttritionRiskScore.employee_id == latest_score_subq.c.employee_id)
            & (AttritionRiskScore.prediction_date == latest_score_subq.c.max_pred_date),
        )
        .subquery()
    )

    # Main query joining departments, roles, and latest risk intelligence
    query = (
        select(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.email,
            Employee.department_id,
            Department.name.label("department_name"),
            Employee.role_id,
            JobRole.title.label("role_title"),
            Employee.manager_id,
            Employee.status,
            Employee.employment_type,
            Employee.work_location,
            Employee.hire_date,
            Employee.probation_end_date,
            Employee.is_active,
            latest_risk_subq.c.flight_risk_prob.label("latest_flight_risk"),
            latest_risk_subq.c.risk_tier.label("latest_risk_tier"),
        )
        .join(Department, Employee.department_id == Department.department_id)
        .join(JobRole, Employee.role_id == JobRole.role_id)
        .outerjoin(latest_risk_subq, Employee.employee_id == latest_risk_subq.c.employee_id)
    )

    # Apply Filters
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if role_id:
        query = query.where(Employee.role_id == role_id)
    if status:
        query = query.where(Employee.status == status)
    if work_location:
        query = query.where(Employee.work_location == work_location)
    if risk_tier:
        query = query.where(latest_risk_subq.c.risk_tier == risk_tier)
    if min_risk_probability is not None:
        query = query.where(
            latest_risk_subq.c.flight_risk_prob >= min_risk_probability
            )

    if max_risk_probability is not None:
        query = query.where(
            latest_risk_subq.c.flight_risk_prob <= max_risk_probability
        )
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Employee.employee_id.ilike(search_pattern),
                Employee.first_name.ilike(search_pattern),
                Employee.last_name.ilike(search_pattern),
                Employee.email.ilike(search_pattern),
            )
        )

    # Compute Total Records
    count_subq = query.subquery()
    total_records = session.execute(select(func.count()).select_from(count_subq)).scalar() or 0

    # Sorting
    sort_column_map = {
        "employee_id": Employee.employee_id,
        "first_name": Employee.first_name,
        "last_name": Employee.last_name,
        "hire_date": Employee.hire_date,
        "department_id": Employee.department_id,
        "status": Employee.status,
        "latest_flight_risk": latest_risk_subq.c.flight_risk_prob,
    }
    col = sort_column_map.get(sort_by, Employee.employee_id)
    order_func = desc if sort_order.lower() == "desc" else asc
    query = query.order_by(order_func(col))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = session.execute(query).mappings().all()

    items = [
        EmployeeSummary(
            employee_id=r["employee_id"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            email=r["email"],
            department_id=r["department_id"],
            department_name=r["department_name"],
            role_id=r["role_id"],
            role_title=r["role_title"],
            manager_id=r["manager_id"],
            status=r["status"],
            employment_type=r["employment_type"],
            work_location=r["work_location"],
            hire_date=r["hire_date"],
            probation_end_date=r["probation_end_date"],
            is_active=r["is_active"],
            latest_flight_risk=float(r["latest_flight_risk"]) if r["latest_flight_risk"] is not None else None,
            latest_risk_tier=r["latest_risk_tier"],
        )
        for r in rows
    ]

    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return PaginatedResponse[EmployeeSummary](
        total=total_records,
        page=page,
        page_size=page_size,
        pages=total_pages,
        data=items,
    )


def get_employee_detail(session: Session, employee_id: str) -> Optional[EmployeeDetail]:
    """
    Constructs comprehensive Employee 360 profile with all longitudinal relationships.
    """
    stmt = (
        select(Employee)
        .options(
            joinedload(Employee.department),
            joinedload(Employee.role),
            joinedload(Employee.manager),
        )
        .where(Employee.employee_id == employee_id)
    )
    emp = session.execute(stmt).unique().scalar_one_or_none()
    if not emp:
        return None

    # Load Skills
    skills_query = (
        select(EmployeeSkill, Skill)
        .join(Skill, EmployeeSkill.skill_id == Skill.skill_id)
        .where(EmployeeSkill.employee_id == employee_id)
    )
    skills = [
        SkillItem(
            skill_id=es.skill_id,
            skill_name=sk.name,
            category=sk.category,
            proficiency_level=es.proficiency_level,
            certified_flag=es.certified_flag,
        )
        for es, sk in session.execute(skills_query).all()
    ]

    # Load Compensation History
    comps = [
        CompensationItem(
            compensation_id=c.compensation_id,
            base_salary=float(c.base_salary),
            bonus_target_pct=float(c.bonus_target_pct),
            stock_options_granted=c.stock_options_granted,
            currency=c.currency,
            effective_from=c.effective_from,
            effective_to=c.effective_to,
            is_current=c.is_current,
            revision_reason=c.revision_reason,
        )
        for c in session.execute(
            select(CompensationRecord)
            .where(CompensationRecord.employee_id == employee_id)
            .order_by(desc(CompensationRecord.effective_from))
        ).scalars().all()
    ]

    # Load Performance Evaluations
    reviews = [
        PerformanceItem(
            evaluation_id=pe.evaluation_id,
            evaluation_cycle=pe.evaluation_cycle,
            rating=pe.rating,
            numeric_score=float(pe.numeric_score),
            goals_met_pct=float(pe.goals_met_pct),
            promotion_readiness=pe.promotion_readiness,
            feedback_summary=pe.feedback_summary,
            evaluation_date=pe.evaluation_date,
        )
        for pe in session.execute(
            select(PerformanceEvaluation)
            .where(PerformanceEvaluation.employee_id == employee_id)
            .order_by(desc(PerformanceEvaluation.evaluation_date))
        ).scalars().all()
    ]

    # Load Engagement Surveys
    surveys = [
        EngagementItem(
            survey_id=s.survey_id,
            survey_date=s.survey_date,
            enps_score=s.enps_score,
            job_satisfaction=s.job_satisfaction,
            work_life_balance=s.work_life_balance,
            management_trust=s.management_trust,
            career_growth_opps=s.career_growth_opps,
            burnout_risk_index=float(s.burnout_risk_index),
            sentiment_score=float(s.sentiment_score),
        )
        for s in session.execute(
            select(EngagementSurvey)
            .where(EngagementSurvey.employee_id == employee_id)
            .order_by(desc(EngagementSurvey.survey_date))
        ).scalars().all()
    ]

    # Load Project Assignments
    assignments = [
        ProjectAssignmentItem(
            assignment_id=pa.assignment_id,
            project_id=pa.project_id,
            project_name=pa.project.name if pa.project else None,
            role_in_project=pa.role_in_project,
            allocation_pct=float(pa.allocation_pct),
            logged_hours_weekly=float(pa.logged_hours_weekly),
            start_date=pa.start_date,
            end_date=pa.end_date,
        )
        for pa in session.execute(
            select(ProjectAssignment)
            .options(joinedload(ProjectAssignment.project))
            .where(ProjectAssignment.employee_id == employee_id)
            .order_by(desc(ProjectAssignment.start_date))
        ).scalars().all()
    ]

    # Load Time Off Records
    leaves = [
        TimeOffItem(
            leave_id=t.leave_id,
            leave_type=t.leave_type,
            start_date=t.start_date,
            end_date=t.end_date,
            is_approved=t.is_approved,
            total_days=t.total_days,
        )
        for t in session.execute(
            select(TimeOffRecord)
            .where(TimeOffRecord.employee_id == employee_id)
            .order_by(desc(TimeOffRecord.start_date))
        ).scalars().all()
    ]

    # Latest Risk Intelligence
    latest_score = session.execute(
        select(AttritionRiskScore)
        .where(AttritionRiskScore.employee_id == employee_id)
        .order_by(desc(AttritionRiskScore.prediction_date))
        .limit(1)
    ).scalar_one_or_none()

    latest_flight_risk = float(latest_score.flight_risk_prob) if latest_score else None
    latest_risk_tier = latest_score.risk_tier if latest_score else None
    drivers = []
    if latest_score:
        if latest_score.top_driver_1:
            drivers.append(f"{latest_score.top_driver_1} ({latest_score.driver_1_shap_val:+.2f})")
        if latest_score.top_driver_2:
            drivers.append(f"{latest_score.top_driver_2} ({latest_score.driver_2_shap_val:+.2f})")
        if latest_score.top_driver_3:
            drivers.append(f"{latest_score.top_driver_3} ({latest_score.driver_3_shap_val:+.2f})")

    dept_mini = (
        DepartmentMini(
            department_id=emp.department.department_id,
            name=emp.department.name,
            division=emp.department.division,
        )
        if emp.department
        else None
    )

    role_mini = (
        RoleMini(
            role_id=emp.role.role_id,
            title=emp.role.title,
            grade_level=emp.role.grade_level,
            is_exempt=emp.role.is_exempt,
        )
        if emp.role
        else None
    )

    manager_mini = (
        ManagerMini(
            employee_id=emp.manager.employee_id,
            first_name=emp.manager.first_name,
            last_name=emp.manager.last_name,
            email=emp.manager.email,
        )
        if emp.manager
        else None
    )

    return EmployeeDetail(
        employee_id=emp.employee_id,
        first_name=emp.first_name,
        last_name=emp.last_name,
        email=emp.email,
        department_id=emp.department_id,
        department=dept_mini,
        role_id=emp.role_id,
        role=role_mini,
        manager_id=emp.manager_id,
        manager=manager_mini,
        status=emp.status,
        employment_type=emp.employment_type,
        work_location=emp.work_location,
        hire_date=emp.hire_date,
        probation_end_date=emp.probation_end_date,
        is_active=emp.is_active,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
        skills=skills,
        compensation_history=comps,
        performance_evaluations=reviews,
        engagement_surveys=surveys,
        project_assignments=assignments,
        time_off_records=leaves,
        latest_flight_risk=latest_flight_risk,
        latest_risk_tier=latest_risk_tier,
        latest_risk_drivers=drivers,
    )
