"""
Labelled Anomaly Injection Engine for WorkforceIQ.
Injects all four mandatory negative organizational anomaly scenarios into clean synthetic data:
- ANOM-01: Post-Termination Activity
- ANOM-02: Circular Management Hierarchy & Orphan Reporting
- ANOM-03: Compensation Inversion & Grade Band Breach
- ANOM-04: Conflicting Leave & Billable Project Logging / Impossible Hours
Generates a ground truth manifest mapping every injected anomaly.
"""

from datetime import date, timedelta
import random
import uuid
from typing import List, Dict, Any, Tuple

from data_generator.config import (
    RANDOM_SEED,
    ANOMALY_QUOTAS,
    GRADE_SALARY_BANDS,
    generate_deterministic_uuid,
)

def inject_anomalies(
    demographics_data: Dict[str, Any],
    longitudinal_data: Dict[str, Any],
    starter_mode: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Injects controlled, labelled anomalies across the 4 mandatory scenarios.
    Returns modified datasets and the ground-truth anomaly manifest.
    """
    random.seed(RANDOM_SEED + 999)
    
    employees = demographics_data["employees"]
    job_roles = demographics_data["job_roles"]
    exit_records = longitudinal_data["exit_records"]
    project_assignments = longitudinal_data["project_assignments"]
    engagement_surveys = longitudinal_data["engagement_surveys"]
    compensation_records = longitudinal_data["compensation_records"]
    time_off_records = longitudinal_data["time_off_records"]
    
    # Scale quotas for starter cohort vs full 10k cohort
    scale = 0.05 if starter_mode else 1.0
    quota_post_term = max(2, int(ANOMALY_QUOTAS["POST_TERMINATION_ACTIVITY"] * scale))
    quota_circular = max(1, int(ANOMALY_QUOTAS["CIRCULAR_HIERARCHY"] * scale))
    quota_comp_inv = max(2, int(ANOMALY_QUOTAS["COMPENSATION_INVERSION"] * scale))
    quota_leave_conflict = max(2, int(ANOMALY_QUOTAS["LEAVE_HOUR_CONFLICT"] * scale))
    
    anomaly_manifest: List[Dict[str, Any]] = []
    
    # Map roles by role_id
    roles_by_id = {r["role_id"]: r for r in job_roles}

    # =========================================================================
    # ANOM-01: Post-Termination Activity
    # =========================================================================
    if exit_records:
        target_exits = random.sample(exit_records, min(quota_post_term, len(exit_records)))
        for ex in target_exits:
            e_id = ex["employee_id"]
            sep_dt = ex["separation_date"]
            post_dt = sep_dt + timedelta(days=random.randint(15, 60))
            
            anom_id = generate_deterministic_uuid()
            if random.random() < 0.5:
                # Injected rogue post-termination project assignment
                assign_id = generate_deterministic_uuid()
                project_assignments.append({
                    "assignment_id": assign_id,
                    "project_id": "PRJ-ENG-001",
                    "employee_id": e_id,
                    "role_in_project": "CONTRIBUTOR",
                    "allocation_pct": 100,
                    "logged_hours_weekly": 40.00,
                    "start_date": post_dt,
                    "end_date": post_dt + timedelta(days=30),
                })
                anomaly_manifest.append({
                    "anomaly_id": anom_id,
                    "anomaly_type": "POST_TERMINATION_ACTIVITY",
                    "severity": "CRITICAL",
                    "entity_type": "project_assignments",
                    "entity_id": assign_id,
                    "target_employee_id": e_id,
                    "description": f"Employee {e_id} recorded project assignment starting on {post_dt}, after separation date {sep_dt}.",
                    "detected_at": "2026-10-30T09:30:00Z",
                    "is_resolved": False,
                })
            else:
                # Injected rogue post-termination engagement survey
                srv_id = generate_deterministic_uuid()
                engagement_surveys.append({
                    "survey_id": srv_id,
                    "employee_id": e_id,
                    "survey_date": post_dt,
                    "enps_score": 8,
                    "job_satisfaction": 4,
                    "work_life_balance": 4,
                    "management_trust": 4,
                    "career_growth_opps": 4,
                    "burnout_risk_index": 0.20,
                    "sentiment_score": 0.50,
                })
                anomaly_manifest.append({
                    "anomaly_id": anom_id,
                    "anomaly_type": "POST_TERMINATION_ACTIVITY",
                    "severity": "CRITICAL",
                    "entity_type": "engagement_surveys",
                    "entity_id": srv_id,
                    "target_employee_id": e_id,
                    "description": f"Employee {e_id} submitted engagement survey on {post_dt}, after separation date {sep_dt}.",
                    "detected_at": "2026-10-30T09:30:00Z",
                    "is_resolved": False,
                })

    # =========================================================================
    # ANOM-02: Circular Management Hierarchy & Orphan Reporting
    # =========================================================================
    # Find candidates with managers who are not the CEO
    mgr_candidates = [
        e for e in employees 
        if e["manager_id"] is not None and e["employee_id"] != "EMP-000001" and e["grade_level"] >= 8
    ]
    
    if len(mgr_candidates) >= 3:
        # 1. Inject Circular Reporting Cycle: A -> B -> C -> A
        c_emps = random.sample(mgr_candidates, 3)
        emp_a, emp_b, emp_c = c_emps[0], c_emps[1], c_emps[2]
        
        emp_a["manager_id"] = emp_b["employee_id"]
        emp_b["manager_id"] = emp_c["employee_id"]
        emp_c["manager_id"] = emp_a["employee_id"]  # Complete the cycle
        
        anom_id = generate_deterministic_uuid()
        anomaly_manifest.append({
            "anomaly_id": anom_id,
            "anomaly_type": "CIRCULAR_HIERARCHY",
            "severity": "HIGH",
            "entity_type": "employees",
            "entity_id": emp_a["employee_id"],
            "target_employee_id": emp_a["employee_id"],
            "description": f"Circular hierarchy loop injected: {emp_a['employee_id']} -> {emp_b['employee_id']} -> {emp_c['employee_id']} -> {emp_a['employee_id']}.",
            "detected_at": "2026-10-30T09:30:00Z",
            "is_resolved": False,
        })
        
        # 2. Inject Orphan / Self-reporting non-CEO nodes
        orphan_candidates = [e for e in employees if e["employee_id"] not in (emp_a["employee_id"], emp_b["employee_id"], emp_c["employee_id"], "EMP-000001")]
        if orphan_candidates:
            num_orphans = min(quota_circular, len(orphan_candidates))
            for o_emp in random.sample(orphan_candidates, num_orphans):
                if random.random() < 0.5:
                    o_emp["manager_id"] = None  # Non-CEO orphan node
                    desc = f"Active non-executive employee {o_emp['employee_id']} has NULL manager_id."
                else:
                    o_emp["manager_id"] = o_emp["employee_id"]  # Self-reporting cycle
                    desc = f"Employee {o_emp['employee_id']} is self-reporting (manager_id == employee_id)."
                    
                anom_id = generate_deterministic_uuid()
                anomaly_manifest.append({
                    "anomaly_id": anom_id,
                    "anomaly_type": "CIRCULAR_HIERARCHY",
                    "severity": "HIGH",
                    "entity_type": "employees",
                    "entity_id": o_emp["employee_id"],
                    "target_employee_id": o_emp["employee_id"],
                    "description": desc,
                    "detected_at": "2026-10-30T09:30:00Z",
                    "is_resolved": False,
                })

    # =========================================================================
    # ANOM-03: Compensation Inversion & Grade Band Breach
    # =========================================================================
    current_comps = [c for c in compensation_records if c.get("is_current") is True]
    if current_comps:
        comp_sample = random.sample(current_comps, min(quota_comp_inv, len(current_comps)))
        for comp in comp_sample:
            e_id = comp["employee_id"]
            grade = comp.get("grade_level", 4)
            band = GRADE_SALARY_BANDS[grade]
            
            anom_id = generate_deterministic_uuid()
            if random.random() < 0.5:
                # Injected salary below minimum
                breach_sal = round(band["min"] - random.uniform(5000, 15000), 2)
                comp["base_salary"] = breach_sal
                desc = f"Salary ${breach_sal:,.2f} for employee {e_id} is below grade {grade} minimum of ${band['min']:,.2f}."
            else:
                # Injected salary above maximum
                breach_sal = round(band["max"] + random.uniform(15000, 45000), 2)
                comp["base_salary"] = breach_sal
                desc = f"Salary ${breach_sal:,.2f} for employee {e_id} exceeds grade {grade} maximum of ${band['max']:,.2f}."
                
            anomaly_manifest.append({
                "anomaly_id": anom_id,
                "anomaly_type": "COMPENSATION_INVERSION",
                "severity": "MEDIUM",
                "entity_type": "compensation_records",
                "entity_id": comp["compensation_id"],
                "target_employee_id": e_id,
                "description": desc,
                "detected_at": "2026-10-30T09:30:00Z",
                "is_resolved": False,
            })

    # =========================================================================
    # ANOM-04: Conflicting Leave & Billable Project Logging / Impossible Hours
    # =========================================================================
    approved_leaves = [l for l in time_off_records if l["is_approved"] is True]
    if approved_leaves:
        leave_sample = random.sample(approved_leaves, min(quota_leave_conflict, len(approved_leaves)))
        for leave in leave_sample:
            e_id = leave["employee_id"]
            l_start = leave["start_date"]
            l_end = leave["end_date"]
            
            anom_id = generate_deterministic_uuid()
            assign_id = generate_deterministic_uuid()
            
            # Injected billable assignment right during approved leave window
            project_assignments.append({
                "assignment_id": assign_id,
                "project_id": "PRJ-ENG-001",
                "employee_id": e_id,
                "role_in_project": "CONTRIBUTOR",
                "allocation_pct": 100,
                "logged_hours_weekly": 45.00,  # Billable work during leave
                "start_date": l_start,
                "end_date": l_end + timedelta(days=7),
            })
            
            anomaly_manifest.append({
                "anomaly_id": anom_id,
                "anomaly_type": "LEAVE_HOUR_CONFLICT",
                "severity": "HIGH",
                "entity_type": "project_assignments",
                "entity_id": assign_id,
                "target_employee_id": e_id,
                "description": f"Employee {e_id} logged 45.0 hrs billable work overlapping with approved leave {l_start} to {l_end}.",
                "detected_at": "2026-10-30T09:30:00Z",
                "is_resolved": False,
            })

    return longitudinal_data, anomaly_manifest
