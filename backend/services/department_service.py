"""
WorkforceIQ Department and Job Role Service Layer.
Provides organizational hierarchy analytics and role band management.
"""

from typing import List, Optional
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models.orm import (
    AttritionRiskScore,
    CompensationRecord,
    Department,
    Employee,
    EngagementSurvey,
    JobRole,
)
from backend.schemas.roles import DepartmentSummary, RoleSummary


def get_departments(session: Session) -> List[DepartmentSummary]:
    """
    Computes department-level workforce aggregates: headcount, average salary,
    average engagement satisfaction, and retention risk counts.
    """
    departments = session.execute(
        select(Department).order_by(Department.department_id)
    ).scalars().all()

    # Pre-aggregate employee metrics per department
    emp_stats = session.execute(
        select(
            Employee.department_id,
            func.count(Employee.employee_id).label("total_headcount"),
            func.sum(case((Employee.is_active == True, 1), else_=0)).label("active_headcount"),
        ).group_by(Employee.department_id)
    ).mappings().all()

    stats_map = {
        r["department_id"]: {
            "total": r["total_headcount"] or 0,
            "active": r["active_headcount"] if r["active_headcount"] is not None else 0,
        }
        for r in emp_stats
    }

    # Pre-aggregate current base salaries
    comp_stats = session.execute(
        select(
            Employee.department_id,
            func.avg(CompensationRecord.base_salary).label("avg_salary"),
        )
        .join(CompensationRecord, Employee.employee_id == CompensationRecord.employee_id)
        .where(CompensationRecord.is_current == True)
        .group_by(Employee.department_id)
    ).mappings().all()

    salary_map = {r["department_id"]: float(r["avg_salary"]) for r in comp_stats if r["avg_salary"]}

    # Pre-aggregate latest engagement satisfaction
    survey_stats = session.execute(
        select(
            Employee.department_id,
            func.avg(EngagementSurvey.job_satisfaction).label("avg_satisfaction"),
        )
        .join(EngagementSurvey, Employee.employee_id == EngagementSurvey.employee_id)
        .group_by(Employee.department_id)
    ).mappings().all()

    survey_map = {r["department_id"]: float(r["avg_satisfaction"]) for r in survey_stats if r["avg_satisfaction"]}

    # Pre-aggregate high/critical flight risk count
    latest_score_date = session.execute(func.max(AttritionRiskScore.prediction_date)).scalar()
    risk_stats = session.execute(
        select(
            Employee.department_id,
            func.count(AttritionRiskScore.score_id).label("high_risk_count"),
        )
        .join(AttritionRiskScore, Employee.employee_id == AttritionRiskScore.employee_id)
        .where(
            AttritionRiskScore.prediction_date == latest_score_date,
            AttritionRiskScore.risk_tier.in_(["HIGH", "CRITICAL"]),
        )
        .group_by(Employee.department_id)
    ).mappings().all()

    risk_map = {r["department_id"]: int(r["high_risk_count"]) for r in risk_stats}

    summaries = []
    for d in departments:
        st = stats_map.get(d.department_id, {"total": 0, "active": 0})
        total = st["total"]
        # Fallback for active headcount count
        active = session.execute(
            select(func.count(Employee.employee_id)).where(
                Employee.department_id == d.department_id, Employee.is_active == True
            )
        ).scalar() or 0
        attrited = total - active

        # Lookup head name
        head_name = None
        if d.head_employee_id:
            head_emp = session.execute(
                select(Employee.first_name, Employee.last_name).where(
                    Employee.employee_id == d.head_employee_id
                )
            ).first()
            if head_emp:
                head_name = f"{head_emp[0]} {head_emp[1]}"

        summaries.append(
            DepartmentSummary(
                department_id=d.department_id,
                name=d.name,
                division=d.division,
                cost_center_code=d.cost_center_code,
                head_employee_id=d.head_employee_id,
                head_name=head_name,
                annual_budget=float(d.annual_budget),
                total_headcount=total,
                active_headcount=active,
                attrited_headcount=attrited,
                average_salary=salary_map.get(d.department_id),
                average_engagement=survey_map.get(d.department_id),
                high_risk_count=risk_map.get(d.department_id, 0),
            )
        )

    return summaries


def get_roles(session: Session, department_id: Optional[str] = None) -> List[RoleSummary]:
    """
    Retrieves job roles with department context and current active headcount.
    """
    query = (
        select(
            JobRole.role_id,
            JobRole.department_id,
            Department.name.label("department_name"),
            JobRole.title,
            JobRole.grade_level,
            JobRole.min_salary,
            JobRole.mid_salary,
            JobRole.max_salary,
            JobRole.is_exempt,
            func.count(Employee.employee_id).label("active_headcount"),
        )
        .join(Department, JobRole.department_id == Department.department_id)
        .outerjoin(
            Employee,
            (JobRole.role_id == Employee.role_id) & (Employee.is_active == True),
        )
    )

    if department_id:
        query = query.where(JobRole.department_id == department_id)

    query = query.group_by(
        JobRole.role_id,
        JobRole.department_id,
        Department.name,
        JobRole.title,
        JobRole.grade_level,
        JobRole.min_salary,
        JobRole.mid_salary,
        JobRole.max_salary,
        JobRole.is_exempt,
    ).order_by(JobRole.department_id, JobRole.grade_level)

    rows = session.execute(query).mappings().all()

    return [
        RoleSummary(
            role_id=r["role_id"],
            department_id=r["department_id"],
            department_name=r["department_name"],
            title=r["title"],
            grade_level=r["grade_level"],
            min_salary=float(r["min_salary"]),
            mid_salary=float(r["mid_salary"]),
            max_salary=float(r["max_salary"]),
            is_exempt=r["is_exempt"],
            active_headcount=r["active_headcount"] or 0,
        )
        for r in rows
    ]


def get_department_detail(session: Session, department_id: str) -> Optional[DepartmentSummary]:
    """
    Retrieves detailed metrics for a single department.
    """
    departments = get_departments(session)
    for d in departments:
        if d.department_id == department_id:
            return d
    return None
