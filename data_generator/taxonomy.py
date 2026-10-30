"""
Master taxonomy and domain catalogs for WorkforceIQ.
Provides standardized definitions for departments, job roles, and skills.
"""

from typing import List, Dict, Any
from data_generator.config import GRADE_SALARY_BANDS

DEPARTMENTS_CATALOG: List[Dict[str, Any]] = [
    {
        "department_id": "DEP-ENG-01",
        "name": "Software Engineering",
        "division": "Product & Engineering",
        "cost_center_code": "CC-ENG-101",
        "annual_budget": 12500000.00,
        "role_prefix": "SWE",
    },
    {
        "department_id": "DEP-AIR-02",
        "name": "AI & Machine Learning Research",
        "division": "Product & Engineering",
        "cost_center_code": "CC-AIR-102",
        "annual_budget": 18000000.00,
        "role_prefix": "AIML",
    },
    {
        "department_id": "DEP-PRD-03",
        "name": "Product Management",
        "division": "Product & Engineering",
        "cost_center_code": "CC-PRD-103",
        "annual_budget": 6500000.00,
        "role_prefix": "PRD",
    },
    {
        "department_id": "DEP-SAL-04",
        "name": "Enterprise Sales",
        "division": "Commercial & Revenue",
        "cost_center_code": "CC-SAL-201",
        "annual_budget": 9500000.00,
        "role_prefix": "SAL",
    },
    {
        "department_id": "DEP-MKT-05",
        "name": "Growth & Product Marketing",
        "division": "Commercial & Revenue",
        "cost_center_code": "CC-MKT-202",
        "annual_budget": 5200000.00,
        "role_prefix": "MKT",
    },
    {
        "department_id": "DEP-CUS-06",
        "name": "Customer Success & Services",
        "division": "Commercial & Revenue",
        "cost_center_code": "CC-CUS-203",
        "annual_budget": 4800000.00,
        "role_prefix": "CSM",
    },
    {
        "department_id": "DEP-PPL-07",
        "name": "People Operations & HR",
        "division": "Corporate Operations",
        "cost_center_code": "CC-PPL-301",
        "annual_budget": 3500000.00,
        "role_prefix": "PPL",
    },
    {
        "department_id": "DEP-FIN-08",
        "name": "Finance, Accounting & Legal",
        "division": "Corporate Operations",
        "cost_center_code": "CC-FIN-302",
        "annual_budget": 4200000.00,
        "role_prefix": "FIN",
    },
]

SKILLS_CATALOG: List[Dict[str, str]] = [
    {"skill_id": "SKL-PY-01", "name": "Python & Data Engineering", "category": "Software Engineering"},
    {"skill_id": "SKL-TS-02", "name": "TypeScript & Frontend Architecture", "category": "Software Engineering"},
    {"skill_id": "SKL-K8S-03", "name": "Kubernetes & Cloud Infrastructure", "category": "Cloud Architecture"},
    {"skill_id": "SKL-DB-04", "name": "Distributed SQL & PostgreSQL", "category": "Data Engineering"},
    {"skill_id": "SKL-ML-05", "name": "Deep Learning & Neural Networks", "category": "AI Research"},
    {"skill_id": "SKL-NLP-06", "name": "Large Language Models & NLP", "category": "AI Research"},
    {"skill_id": "SKL-PRD-07", "name": "Product Strategy & Roadmapping", "category": "Product Management"},
    {"skill_id": "SKL-UX-08", "name": "User Experience & Design Systems", "category": "Design"},
    {"skill_id": "SKL-ENT-09", "name": "Enterprise B2B Deal Closing", "category": "Sales"},
    {"skill_id": "SKL-SOL-10", "name": "Pre-Sales Solutions Engineering", "category": "Sales Engineering"},
    {"skill_id": "SKL-HR-11", "name": "Talent Acquisition & Compensation Planning", "category": "Human Resources"},
    {"skill_id": "SKL-FIN-12", "name": "Corporate Financial Modeling & GAAP", "category": "Finance"},
]

def generate_job_roles_catalog() -> List[Dict[str, Any]]:
    """Build standardized job roles for each department across grade tiers 1 to 15."""
    roles = []
    
    # Titles templates per department
    dept_titles = {
        "DEP-ENG-01": "Software Engineer",
        "DEP-AIR-02": "AI Research Scientist",
        "DEP-PRD-03": "Product Manager",
        "DEP-SAL-04": "Account Executive",
        "DEP-MKT-05": "Marketing Manager",
        "DEP-CUS-06": "Customer Success Manager",
        "DEP-PPL-07": "People Partner",
        "DEP-FIN-08": "Financial Analyst",
    }
    
    for dept in DEPARTMENTS_CATALOG:
        dept_id = dept["department_id"]
        prefix = dept["role_prefix"]
        base_title = dept_titles.get(dept_id, "Specialist")
        
        for grade in range(1, 16):
            band = GRADE_SALARY_BANDS[grade]
            
            # Format title
            if grade == 15:
                title = f"Chief {base_title.split()[0]} Officer" if "DEP-ENG" in dept_id or "DEP-AIR" in dept_id else f"Chief Officer ({dept['name']})"
                is_exempt = True
            elif grade == 14:
                title = f"Vice President of {dept['name']}"
                is_exempt = True
            elif grade == 13:
                title = f"Senior Director, {dept['name']}"
                is_exempt = True
            elif grade == 12:
                title = f"Director of {dept['name']}"
                is_exempt = True
            elif grade == 11:
                title = f"Senior Manager, {base_title}"
                is_exempt = True
            elif grade == 10:
                title = f"Engineering Manager" if "ENG" in prefix else f"Manager, {base_title}"
                is_exempt = True
            else:
                title = f"{band['title_prefix']} {base_title}"
                is_exempt = grade >= 3
                
            role_id = f"ROLE-{prefix}-{grade:02d}"
            roles.append({
                "role_id": role_id,
                "department_id": dept_id,
                "title": title,
                "grade_level": grade,
                "min_salary": band["min"],
                "mid_salary": band["mid"],
                "max_salary": band["max"],
                "is_exempt": is_exempt,
            })
            
    return roles
