"""
Demographic and Core Employee Profile Generator for WorkforceIQ.
Builds deterministic parent entities, reporting hierarchy (DAG), and skill matrices.
"""

from datetime import date, timedelta
import random
from typing import List, Dict, Any, Tuple
from faker import Faker
import numpy as np

from data_generator.config import (
    RANDOM_SEED,
    SIMULATION_START_DATE,
    SIMULATION_END_DATE,
    HISTORICAL_LOOKBACK_YEARS,
    GRADE_SALARY_BANDS,
)
from data_generator.taxonomy import (
    DEPARTMENTS_CATALOG,
    SKILLS_CATALOG,
    generate_job_roles_catalog,
)

# Department allocation weights
DEPT_WEIGHTS = {
    "DEP-ENG-01": 0.35,  # Software Engineering
    "DEP-AIR-02": 0.20,  # AI Research
    "DEP-PRD-03": 0.10,  # Product
    "DEP-SAL-04": 0.15,  # Sales
    "DEP-MKT-05": 0.08,  # Marketing
    "DEP-CUS-06": 0.06,  # Customer Success
    "DEP-PPL-07": 0.03,  # People Operations
    "DEP-FIN-08": 0.03,  # Finance
}

def generate_core_demographics(num_employees: int) -> Dict[str, Any]:
    """
    Generates parent catalogs and master employee population with valid hierarchy DAG.
    Parent records generated before dependent records.
    """
    fake = Faker()
    Faker.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
    # 1. Master Catalogs (Parent Records)
    departments = [dict(d) for d in DEPARTMENTS_CATALOG]
    job_roles = generate_job_roles_catalog()
    skills = [dict(s) for s in SKILLS_CATALOG]
    
    # Map roles by department and grade for fast indexing
    roles_by_dept_grade = {}
    for r in job_roles:
        key = (r["department_id"], r["grade_level"])
        roles_by_dept_grade[key] = r["role_id"]
        
    dept_ids = [d["department_id"] for d in departments]
    dept_probs = [DEPT_WEIGHTS[did] for did in dept_ids]
    
    employees: List[Dict[str, Any]] = []
    employee_skills: List[Dict[str, Any]] = []
    
    # Used emails set for guaranteed uniqueness
    used_emails = set()
    
    # Earliest possible hire date: 6 years before simulation start
    earliest_hire = SIMULATION_START_DATE - timedelta(days=HISTORICAL_LOOKBACK_YEARS * 365)
    
    # -------------------------------------------------------------------------
    # Hierarchy Stratification Setup
    # 1 CEO, VPs, Directors, Managers, and Individual Contributors (ICs)
    # -------------------------------------------------------------------------
    num_vps = len(departments)  # 1 VP per department
    num_directors = max(int(num_employees * 0.02), len(departments) * 2)
    num_managers = max(int(num_employees * 0.08), len(departments) * 4)
    num_ics = num_employees - (1 + num_vps + num_directors + num_managers)
    
    if num_ics < 0:
        # Adjustment for very small starter cohorts
        num_vps = max(1, int(num_employees * 0.05))
        num_directors = max(1, int(num_employees * 0.08))
        num_managers = max(1, int(num_employees * 0.15))
        num_ics = num_employees - (1 + num_vps + num_directors + num_managers)
        
    emp_counter = 1
    
    # Helper to generate unique email
    def make_email(first: str, last: str) -> str:
        clean_first = "".join(c for c in first.lower() if c.isalnum())
        clean_last = "".join(c for c in last.lower() if c.isalnum())
        base = f"{clean_first}.{clean_last}@yottaflex.ai"
        if base not in used_emails:
            used_emails.add(base)
            return base
        idx = 2
        while f"{clean_first}.{clean_last}{idx}@yottaflex.ai" in used_emails:
            idx += 1
        email = f"{clean_first}.{clean_last}{idx}@yottaflex.ai"
        used_emails.add(email)
        return email

    # 1. Chief Executive Officer (CEO) - EMP-000001
    ceo_id = f"EMP-{emp_counter:06d}"
    emp_counter += 1
    ceo_first = fake.first_name()
    ceo_last = fake.last_name()
    ceo_dept = "DEP-ENG-01"
    ceo_hire = earliest_hire + timedelta(days=random.randint(0, 365))
    
    ceo = {
        "employee_id": ceo_id,
        "first_name": ceo_first,
        "last_name": ceo_last,
        "email": make_email(ceo_first, ceo_last),
        "department_id": ceo_dept,
        "role_id": roles_by_dept_grade[(ceo_dept, 15)],
        "manager_id": None,  # CEO has no manager
        "status": "ACTIVE",
        "employment_type": "FULL_TIME",
        "work_location": "HYBRID",
        "hire_date": ceo_hire,
        "probation_end_date": ceo_hire + timedelta(days=90),
        "is_active": True,
        "grade_level": 15,
    }
    employees.append(ceo)
    
    # 2. Vice Presidents (VPs) - Grade 14, reporting to CEO
    vp_ids_by_dept = {}
    for dept in departments:
        if emp_counter > num_employees:
            break
        vp_id = f"EMP-{emp_counter:06d}"
        emp_counter += 1
        d_id = dept["department_id"]
        vp_first = fake.first_name()
        vp_last = fake.last_name()
        vp_hire = earliest_hire + timedelta(days=random.randint(30, 700))
        
        vp = {
            "employee_id": vp_id,
            "first_name": vp_first,
            "last_name": vp_last,
            "email": make_email(vp_first, vp_last),
            "department_id": d_id,
            "role_id": roles_by_dept_grade[(d_id, 14)],
            "manager_id": ceo_id,  # VPs report to CEO
            "status": "ACTIVE",
            "employment_type": "FULL_TIME",
            "work_location": "HYBRID",
            "hire_date": vp_hire,
            "probation_end_date": vp_hire + timedelta(days=90),
            "is_active": True,
            "grade_level": 14,
        }
        employees.append(vp)
        vp_ids_by_dept[d_id] = vp_id
        # Update department head_employee_id
        dept["head_employee_id"] = vp_id

    # 3. Directors - Grades 12-13, reporting to Department VPs
    director_ids_by_dept = {d["department_id"]: [] for d in departments}
    for _ in range(num_directors):
        if emp_counter > num_employees:
            break
        dir_id = f"EMP-{emp_counter:06d}"
        emp_counter += 1
        d_id = np.random.choice(dept_ids, p=dept_probs)
        manager_id = vp_ids_by_dept.get(d_id, ceo_id)
        grade = random.choice([12, 13])
        dir_first = fake.first_name()
        dir_last = fake.last_name()
        dir_hire = earliest_hire + timedelta(days=random.randint(100, 1000))
        
        dir_emp = {
            "employee_id": dir_id,
            "first_name": dir_first,
            "last_name": dir_last,
            "email": make_email(dir_first, dir_last),
            "department_id": d_id,
            "role_id": roles_by_dept_grade[(d_id, grade)],
            "manager_id": manager_id,
            "status": "ACTIVE",
            "employment_type": "FULL_TIME",
            "work_location": random.choice(["ONSITE", "HYBRID", "REMOTE"]),
            "hire_date": dir_hire,
            "probation_end_date": dir_hire + timedelta(days=90),
            "is_active": True,
            "grade_level": grade,
        }
        employees.append(dir_emp)
        director_ids_by_dept[d_id].append(dir_id)

    # 4. Managers - Grades 10-11, reporting to Directors
    manager_ids_by_dept = {d["department_id"]: [] for d in departments}
    for _ in range(num_managers):
        if emp_counter > num_employees:
            break
        mgr_id = f"EMP-{emp_counter:06d}"
        emp_counter += 1
        d_id = np.random.choice(dept_ids, p=dept_probs)
        possible_dirs = director_ids_by_dept.get(d_id, [])
        manager_id = random.choice(possible_dirs) if possible_dirs else vp_ids_by_dept.get(d_id, ceo_id)
        grade = random.choice([10, 11])
        mgr_first = fake.first_name()
        mgr_last = fake.last_name()
        mgr_hire = earliest_hire + timedelta(days=random.randint(200, 1400))
        
        mgr_emp = {
            "employee_id": mgr_id,
            "first_name": mgr_first,
            "last_name": mgr_last,
            "email": make_email(mgr_first, mgr_last),
            "department_id": d_id,
            "role_id": roles_by_dept_grade[(d_id, grade)],
            "manager_id": manager_id,
            "status": "ACTIVE",
            "employment_type": "FULL_TIME",
            "work_location": random.choice(["ONSITE", "HYBRID", "REMOTE"]),
            "hire_date": mgr_hire,
            "probation_end_date": mgr_hire + timedelta(days=90),
            "is_active": True,
            "grade_level": grade,
        }
        employees.append(mgr_emp)
        manager_ids_by_dept[d_id].append(mgr_id)

    # 5. Individual Contributors (ICs) - Grades 1 to 9, reporting to Managers
    # Distribute grades with standard organizational pyramid (more junior/mid, fewer principal)
    ic_grade_dist = [0.18, 0.22, 0.24, 0.15, 0.10, 0.05, 0.03, 0.02, 0.01]  # Grades 1 to 9
    
    sim_days_span = (SIMULATION_END_DATE - earliest_hire).days
    
    while emp_counter <= num_employees:
        ic_id = f"EMP-{emp_counter:06d}"
        emp_counter += 1
        d_id = np.random.choice(dept_ids, p=dept_probs)
        possible_mgrs = manager_ids_by_dept.get(d_id, [])
        manager_id = random.choice(possible_mgrs) if possible_mgrs else vp_ids_by_dept.get(d_id, ceo_id)
        
        grade = int(np.random.choice(range(1, 10), p=ic_grade_dist))
        ic_first = fake.first_name()
        ic_last = fake.last_name()
        
        # 75% historical hires, 25% hired during the 24-month observation window
        if random.random() < 0.75:
            # Historical hire (before SIMULATION_START_DATE)
            pre_sim_days = (SIMULATION_START_DATE - earliest_hire).days
            hire_dt = earliest_hire + timedelta(days=random.randint(0, pre_sim_days))
        else:
            # Inflow hire during simulation
            in_sim_days = (SIMULATION_END_DATE - SIMULATION_START_DATE).days - 60  # at least 2 months tenure
            hire_dt = SIMULATION_START_DATE + timedelta(days=random.randint(0, max(1, in_sim_days)))
            
        probation_end = hire_dt + timedelta(days=90)
        
        ic_emp = {
            "employee_id": ic_id,
            "first_name": ic_first,
            "last_name": ic_last,
            "email": make_email(ic_first, ic_last),
            "department_id": d_id,
            "role_id": roles_by_dept_grade[(d_id, grade)],
            "manager_id": manager_id,
            "status": "ACTIVE",
            "employment_type": np.random.choice(
                ["FULL_TIME", "PART_TIME", "CONTRACTOR", "INTERN"],
                p=[0.88, 0.05, 0.05, 0.02] if grade <= 2 else [0.96, 0.02, 0.02, 0.00]
            ),
            "work_location": np.random.choice(["ONSITE", "HYBRID", "REMOTE"], p=[0.25, 0.55, 0.20]),
            "hire_date": hire_dt,
            "probation_end_date": probation_end,
            "is_active": True,
            "grade_level": grade,
        }
        employees.append(ic_emp)

    # 6. Assign Skills (2 to 5 skills per employee)
    all_skill_ids = [s["skill_id"] for s in skills]
    
    # Map departments to relevant skill bias
    dept_skill_pref = {
        "DEP-ENG-01": ["SKL-PY-01", "SKL-TS-02", "SKL-K8S-03", "SKL-DB-04"],
        "DEP-AIR-02": ["SKL-PY-01", "SKL-DB-04", "SKL-ML-05", "SKL-NLP-06"],
        "DEP-PRD-03": ["SKL-PRD-07", "SKL-UX-08", "SKL-TS-02"],
        "DEP-SAL-04": ["SKL-ENT-09", "SKL-SOL-10"],
        "DEP-MKT-05": ["SKL-UX-08", "SKL-ENT-09", "SKL-PRD-07"],
        "DEP-CUS-06": ["SKL-SOL-10", "SKL-ENT-09", "SKL-TS-02"],
        "DEP-PPL-07": ["SKL-HR-11"],
        "DEP-FIN-08": ["SKL-FIN-12"],
    }
    
    for emp in employees:
        e_id = emp["employee_id"]
        d_id = emp["department_id"]
        preferred = dept_skill_pref.get(d_id, [])
        num_skills = random.randint(2, 5)
        
        # Pick from preferred plus random others
        chosen = set(random.sample(preferred, min(len(preferred), random.randint(1, len(preferred)))))
        while len(chosen) < num_skills:
            chosen.add(random.choice(all_skill_ids))
            
        for s_id in chosen:
            # Higher grade correlates with higher proficiency
            base_prof = min(5, max(1, int(emp["grade_level"] / 3) + random.randint(0, 2)))
            employee_skills.append({
                "employee_id": e_id,
                "skill_id": s_id,
                "proficiency_level": base_prof,
                "certified_flag": random.random() < 0.35,
            })
            
    return {
        "departments": departments,
        "job_roles": job_roles,
        "skills": skills,
        "employees": employees,
        "employee_skills": employee_skills,
    }
