"""
Longitudinal Workforce History Simulator for WorkforceIQ.
Generates 24 months of promotions, compensation revisions (SCD2), performance appraisals,
engagement pulse surveys with missingness, project allocations, time off,
flight risk assessments, retention interventions, and 5-15% voluntary attrition.
"""

from datetime import date, timedelta
import random
import uuid
from typing import List, Dict, Any, Tuple
import numpy as np

from data_generator.config import (
    RANDOM_SEED,
    SIMULATION_START_DATE,
    SIMULATION_END_DATE,
    GRADE_SALARY_BANDS,
    SURVEY_MISSINGNESS_RATE,
    TARGET_VOLUNTARY_ATTRITION_RATE,
    INVOLUNTARY_ATTRITION_RATE,
    RETIREMENT_ATTRITION_RATE,
    generate_deterministic_uuid,
)

def simulate_workforce_history(demographics_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates 24-month longitudinal operational history for the employee cohort.
    Ensures strict temporal ordering and pre-outcome feature boundaries.
    """
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
    employees = demographics_data["employees"]
    job_roles = demographics_data["job_roles"]
    departments = demographics_data["departments"]
    
    roles_by_dept_grade = {
        (r["department_id"], r["grade_level"]): r for r in job_roles
    }
    
    # Target containers
    compensation_records: List[Dict[str, Any]] = []
    employee_history: List[Dict[str, Any]] = []
    performance_evaluations: List[Dict[str, Any]] = []
    engagement_surveys: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []
    project_assignments: List[Dict[str, Any]] = []
    time_off_records: List[Dict[str, Any]] = []
    attrition_risk_scores: List[Dict[str, Any]] = []
    retention_interventions: List[Dict[str, Any]] = []
    exit_records: List[Dict[str, Any]] = []
    
    # -------------------------------------------------------------------------
    # 1. Projects Portfolio Setup (3-5 projects per department)
    # -------------------------------------------------------------------------
    proj_names = [
        "Core Platform Modernization", "Next-Gen ML Inference Engine",
        "Autonomous Agents Framework", "Enterprise Data Fabric",
        "Cloud Cost Optimization", "Global Revenue Expansion",
        "Strategic Partner Integrations", "Customer Retention Analytics",
        "Security Zero-Trust Overhaul", "Continuous CI/CD Delivery Pipeline",
    ]
    proj_counter = 1
    projects_by_dept = {d["department_id"]: [] for d in departments}
    
    for dept in departments:
        d_id = dept["department_id"]
        for p_idx in range(random.randint(3, 5)):
            p_id = f"PRJ-{d_id.split('-')[1]}-{proj_counter:03d}"
            proj_counter += 1
            p_name = f"{d_id.split('-')[1]} - {random.choice(proj_names)}"
            p_start = SIMULATION_START_DATE - timedelta(days=random.randint(60, 365))
            p_end = SIMULATION_END_DATE + timedelta(days=random.randint(90, 365))
            
            proj = {
                "project_id": p_id,
                "department_id": d_id,
                "name": p_name,
                "priority": random.choice(["MEDIUM", "HIGH", "CRITICAL"]),
                "start_date": p_start,
                "end_date": p_end,
                "is_billable": random.random() < 0.85,
            }
            projects.append(proj)
            projects_by_dept[d_id].append(p_id)

    # -------------------------------------------------------------------------
    # 2. Base Compensation & Initial SCD2 History Generation
    # -------------------------------------------------------------------------
    for emp in employees:
        e_id = emp["employee_id"]
        d_id = emp["department_id"]
        grade = emp["grade_level"]
        role = roles_by_dept_grade[(d_id, grade)]
        hire_dt = emp["hire_date"]
        
        # Calculate initial salary with standard distribution centered around midpoint
        mid = role["mid_salary"]
        salary_spread = (role["max_salary"] - role["min_salary"]) * 0.35
        base_salary = round(float(np.clip(
            np.random.normal(mid, salary_spread * 0.4),
            role["min_salary"] + 500,
            role["max_salary"] - 500
        )), 2)
        
        bonus_pct = round(min(50.0, max(0.0, (grade - 1) * 2.5 + random.uniform(0, 5))), 2)
        stock_shares = int(max(0, (grade - 4) * 250 + random.randint(0, 500))) if grade >= 5 else 0
        
        # Initial Compensation (SCD2)
        comp_id = generate_deterministic_uuid()
        comp_record = {
            "compensation_id": comp_id,
            "employee_id": e_id,
            "base_salary": base_salary,
            "bonus_target_pct": bonus_pct,
            "stock_options_granted": stock_shares,
            "currency": "USD",
            "effective_from": hire_dt,
            "effective_to": None,
            "is_current": True,
            "revision_reason": "HIRE",
            "grade_level": grade,
        }
        compensation_records.append(comp_record)
        
        # Initial Employee Movement History (SCD2)
        hist_id = generate_deterministic_uuid()
        hist_record = {
            "history_id": hist_id,
            "employee_id": e_id,
            "department_id": d_id,
            "role_id": role["role_id"],
            "manager_id": emp["manager_id"],
            "status": "ACTIVE",
            "effective_from": hire_dt,
            "effective_to": None,
            "is_current": True,
            "change_reason": "HIRE",
            "grade_level": grade,
        }
        employee_history.append(hist_record)

    # -------------------------------------------------------------------------
    # 3. Simulate 24 Calendar Months (Quarterly & Biannual Cycles)
    # Nov 2024 to Oct 2026
    # -------------------------------------------------------------------------
    # Quarterly survey dates (8 quarters)
    survey_dates = [
        date(2024, 12, 15), date(2025, 3, 15), date(2025, 6, 15), date(2025, 9, 15),
        date(2025, 12, 15), date(2026, 3, 15), date(2026, 6, 15), date(2026, 9, 15),
    ]
    # Biannual evaluation cycles
    eval_cycles = [
        ("2024-H2", date(2024, 12, 31)),
        ("2025-H1", date(2025, 6, 30)),
        ("2025-H2", date(2025, 12, 31)),
        ("2026-H1", date(2026, 6, 30)),
    ]
    
    # Track mutable active state and current attributes during simulation
    emp_state = {}
    for emp in employees:
        e_id = emp["employee_id"]
        emp_state[e_id] = {
            "is_active": True,
            "separation_date": None,
            "current_grade": emp["grade_level"],
            "current_dept": emp["department_id"],
            "current_role": emp["role_id"],
            "current_manager": emp["manager_id"],
            "hire_date": emp["hire_date"],
            # Base latent sentiment traits for continuity
            "latent_sentiment": random.uniform(-0.2, 0.6),
            "latent_burnout": random.uniform(0.1, 0.45),
            "latent_performance": random.uniform(2.8, 4.4),
            "comp_ref": next(c for c in compensation_records if c["employee_id"] == e_id),
            "hist_ref": next(h for h in employee_history if h["employee_id"] == e_id),
        }
        
    # Map employees by ID for fast lookup
    emp_lookup = {e["employee_id"]: e for e in employees}

    # Iterate through quarters
    for q_idx, q_date in enumerate(survey_dates):
        
        # A. Performance Appraisals (Triggered if end of H1 / H2)
        for cycle_name, cycle_dt in eval_cycles:
            if cycle_dt <= q_date < cycle_dt + timedelta(days=90):
                for e_id, st in emp_state.items():
                    if not st["is_active"] or st["hire_date"] > cycle_dt - timedelta(days=60):
                        continue
                    
                    # Compute review rating
                    num_score = round(float(np.clip(
                        np.random.normal(st["latent_performance"], 0.4), 1.0, 5.0
                    )), 2)
                    
                    if num_score >= 4.5:
                        rating = "OUTSTANDING"
                        readiness = "READY_NOW"
                    elif num_score >= 3.8:
                        rating = "EXCEEDS_EXPECTATIONS"
                        readiness = "READY_NOW" if st["current_grade"] < 13 else "DEVELOPING"
                    elif num_score >= 2.8:
                        rating = "MEETS_EXPECTATIONS"
                        readiness = "DEVELOPING"
                    elif num_score >= 2.0:
                        rating = "NEEDS_IMPROVEMENT"
                        readiness = "NOT_READY"
                    else:
                        rating = "UNSATISFACTORY"
                        readiness = "NOT_READY"
                        
                    goals_pct = round(float(np.clip(num_score * 25.0 + random.uniform(-10, 15), 20.0, 140.0)), 2)
                    manager_id = st["current_manager"] or e_id
                    
                    performance_evaluations.append({
                        "evaluation_id": generate_deterministic_uuid(),
                        "employee_id": e_id,
                        "reviewer_id": manager_id,
                        "evaluation_cycle": cycle_name,
                        "rating": rating,
                        "numeric_score": num_score,
                        "goals_met_pct": goals_pct,
                        "promotion_readiness": readiness,
                        "feedback_summary": f"Performance evaluation for {cycle_name}. Rated as {rating}.",
                        "evaluation_date": cycle_dt,
                    })

        # B. Promotions & Annual Merit Adjustments (SCD Type 2)
        # Promotes ~2.5% of active employees per quarter (cumulative ~10-12% over 24 months)
        if q_idx in (1, 3, 5, 7):  # semi-annual review points
            for e_id, st in emp_state.items():
                if not st["is_active"] or st["current_grade"] >= 14 or st["hire_date"] > q_date - timedelta(days=180):
                    continue
                
                # Promotion candidate
                if st["latent_performance"] >= 3.9 and random.random() < 0.08:
                    old_grade = st["current_grade"]
                    new_grade = old_grade + 1
                    d_id = st["current_dept"]
                    new_role = roles_by_dept_grade[(d_id, new_grade)]
                    
                    # Close old SCD2 history
                    old_hist = st["hist_ref"]
                    old_hist["effective_to"] = q_date
                    old_hist["is_current"] = False
                    
                    # Insert new SCD2 history
                    new_hist = {
                        "history_id": generate_deterministic_uuid(),
                        "employee_id": e_id,
                        "department_id": d_id,
                        "role_id": new_role["role_id"],
                        "manager_id": st["current_manager"],
                        "status": "ACTIVE",
                        "effective_from": q_date,
                        "effective_to": None,
                        "is_current": True,
                        "change_reason": "PROMOTION",
                        "grade_level": new_grade,
                    }
                    employee_history.append(new_hist)
                    st["hist_ref"] = new_hist
                    st["current_grade"] = new_grade
                    st["current_role"] = new_role["role_id"]
                    
                    # Close old SCD2 compensation
                    old_comp = st["comp_ref"]
                    old_comp["effective_to"] = q_date
                    old_comp["is_current"] = False
                    
                    # 12-18% promotional raise
                    new_sal = round(max(
                        old_comp["base_salary"] * random.uniform(1.12, 1.18),
                        new_role["min_salary"] + 1000
                    ), 2)
                    new_comp = {
                        "compensation_id": generate_deterministic_uuid(),
                        "employee_id": e_id,
                        "base_salary": new_sal,
                        "bonus_target_pct": min(50.0, old_comp["bonus_target_pct"] + 2.5),
                        "stock_options_granted": old_comp["stock_options_granted"] + (new_grade * 100),
                        "currency": "USD",
                        "effective_from": q_date,
                        "effective_to": None,
                        "is_current": True,
                        "revision_reason": "PROMOTION",
                        "grade_level": new_grade,
                    }
                    compensation_records.append(new_comp)
                    st["comp_ref"] = new_comp
                    st["latent_sentiment"] = min(0.9, st["latent_sentiment"] + 0.25)
                    st["latent_burnout"] = max(0.1, st["latent_burnout"] - 0.15)

        # C. Engagement Pulse Surveys (With realistic non-response missingness)
        for e_id, st in emp_state.items():
            if not st["is_active"] or st["hire_date"] > q_date:
                continue
                
            # Simulate survey missingness / non-response (~8%)
            if random.random() < SURVEY_MISSINGNESS_RATE:
                continue
                
            # Random walk for sentiment & burnout
            st["latent_sentiment"] = float(np.clip(
                st["latent_sentiment"] + random.uniform(-0.12, 0.10), -0.85, 0.85
            ))
            st["latent_burnout"] = float(np.clip(
                st["latent_burnout"] + random.uniform(-0.08, 0.10), 0.05, 0.95
            ))
            
            # Map continuous sentiment to 1-5 Likert scales
            base_likert = int(np.clip(round((st["latent_sentiment"] + 1.0) * 2.0 + 1.0), 1, 5))
            job_sat = int(np.clip(base_likert + random.choice([-1, 0, 0, 1]), 1, 5))
            wlb = int(np.clip(int((1.0 - st["latent_burnout"]) * 4.0 + 1.0) + random.choice([0, 0, -1]), 1, 5))
            mgmt_trust = int(np.clip(base_likert + random.choice([-1, 0, 0, 0, 1]), 1, 5))
            growth_opps = int(np.clip(base_likert + (1 if st["current_grade"] <= 5 else 0), 1, 5))
            
            enps = int(np.clip(round((job_sat + mgmt_trust) / 10.0 * 10.0 + random.uniform(-1, 1)), 0, 10))
            
            engagement_surveys.append({
                "survey_id": generate_deterministic_uuid(),
                "employee_id": e_id,
                "survey_date": q_date,
                "enps_score": enps,
                "job_satisfaction": job_sat,
                "work_life_balance": wlb,
                "management_trust": mgmt_trust,
                "career_growth_opps": growth_opps,
                "burnout_risk_index": round(st["latent_burnout"], 2),
                "sentiment_score": round(st["latent_sentiment"], 2),
            })

        # D. Project Assignments & Time Off Generation
        for e_id, st in emp_state.items():
            if not st["is_active"] or st["hire_date"] > q_date:
                continue
            
            # Allocate to department project if not already assigned this quarter
            d_id = st["current_dept"]
            dept_projs = projects_by_dept.get(d_id, [])
            if dept_projs and random.random() < 0.80:
                p_id = random.choice(dept_projs)
                logged_hrs = round(float(np.clip(
                    40.0 + (st["latent_burnout"] * 18.0) + random.uniform(-3, 6), 35.0, 65.0
                )), 2)
                
                project_assignments.append({
                    "assignment_id": generate_deterministic_uuid(),
                    "project_id": p_id,
                    "employee_id": e_id,
                    "role_in_project": "TECH_LEAD" if st["current_grade"] >= 8 else "CONTRIBUTOR",
                    "allocation_pct": 100,
                    "logged_hours_weekly": logged_hrs,
                    "start_date": q_date - timedelta(days=45),
                    "end_date": q_date + timedelta(days=45),
                })
                
            # Random approved leave during quarter
            if random.random() < 0.25:
                leave_start = q_date - timedelta(days=random.randint(10, 50))
                leave_days = random.choice([1.0, 2.0, 3.0, 5.0, 10.0])
                time_off_records.append({
                    "leave_id": generate_deterministic_uuid(),
                    "employee_id": e_id,
                    "leave_type": random.choice(["ANNUAL", "SICK", "BEREAVEMENT"]),
                    "start_date": leave_start,
                    "end_date": leave_start + timedelta(days=int(leave_days)),
                    "is_approved": True,
                    "total_days": leave_days,
                })

        # E. Flight Risk Scoring & Proactive Retention Interventions
        for e_id, st in emp_state.items():
            if not st["is_active"] or st["hire_date"] > q_date:
                continue
            
            # Compute objective pre-outcome flight risk probability
            cur_comp = st["comp_ref"]
            role_mid = roles_by_dept_grade[(st["current_dept"], st["current_grade"])]["mid_salary"]
            compa_ratio = cur_comp["base_salary"] / role_mid
            
            # Realistic continuous flight risk formula based on domain drivers
            base_comp_factor = max(0.0, (1.05 - compa_ratio) * 0.45)
            burnout_factor = max(0.0, (st["latent_burnout"] - 0.25) * 0.65)
            sentiment_factor = max(0.0, (0.25 - st["latent_sentiment"]) * 0.35)
            tenure_factor = min(0.18, (q_date - st["hire_date"]).days / 365.0 * 0.04)
            
            risk_raw = 0.08 + base_comp_factor + burnout_factor + sentiment_factor + tenure_factor
            flight_prob = float(np.clip(risk_raw + random.uniform(-0.04, 0.04), 0.020, 0.980))
            
            # Assign risk tier
            if flight_prob >= 0.75:
                tier = "CRITICAL"
            elif flight_prob >= 0.55:
                tier = "HIGH"
            elif flight_prob >= 0.30:
                tier = "MEDIUM"
            else:
                tier = "LOW"
                
            score_id = generate_deterministic_uuid()
            attrition_risk_scores.append({
                "score_id": score_id,
                "employee_id": e_id,
                "prediction_date": q_date,
                "flight_risk_prob": round(flight_prob, 3),
                "risk_tier": tier,
                "model_version": "v1.0.0",
                "top_driver_1": "compa_ratio_low" if compa_ratio < 0.95 else "burnout_risk_high",
                "driver_1_shap_val": round(0.28 + random.uniform(-0.05, 0.08), 4),
                "top_driver_2": "work_life_balance_low" if st["latent_burnout"] > 0.45 else "time_in_role",
                "driver_2_shap_val": round(0.18 + random.uniform(-0.04, 0.05), 4),
                "top_driver_3": "management_trust_low",
                "driver_3_shap_val": round(0.09 + random.uniform(-0.02, 0.04), 4),
            })
            
            # Proactive Retention Intervention Trigger (Rule BR-INT-01)
            # If Risk is HIGH or CRITICAL, HR triggers an intervention
            if tier in ("HIGH", "CRITICAL") and random.random() < 0.80:
                intv_type = "COMPENSATION_INCREASE" if compa_ratio < 0.92 else "RETENTION_BONUS"
                intv_cost = 10000.0 if intv_type == "RETENTION_BONUS" else 15000.0
                
                # Intervention success odds: 60% employee accepts and is retained
                accepted = random.random() < 0.60
                
                retention_interventions.append({
                    "intervention_id": generate_deterministic_uuid(),
                    "employee_id": e_id,
                    "risk_score_id": score_id,
                    "intervention_type": intv_type,
                    "status": "ACCEPTED" if accepted else "DECLINED",
                    "cost_usd": intv_cost,
                    "proposed_date": q_date,
                    "action_date": q_date + timedelta(days=14),
                    "outcome_evaluated_date": q_date + timedelta(days=180),
                    "is_successful": accepted,
                    "hr_notes": f"Proactive retention workflow triggered for tier {tier}.",
                })
                
                if accepted:
                    # Mitigate risk
                    st["latent_sentiment"] += 0.30
                    st["latent_burnout"] -= 0.20

    # -------------------------------------------------------------------------
    # 4. Attrition Outcome Generation (Strict 5% - 15% Voluntary Attrition)
    # -------------------------------------------------------------------------
    # Calculate target number of voluntary departures
    total_active_pool = [e_id for e_id, st in emp_state.items() if (SIMULATION_END_DATE - st["hire_date"]).days >= 90]
    
    target_vol_count = int(len(total_active_pool) * TARGET_VOLUNTARY_ATTRITION_RATE)
    target_invol_count = int(len(total_active_pool) * INVOLUNTARY_ATTRITION_RATE)
    target_retire_count = int(len(total_active_pool) * RETIREMENT_ATTRITION_RATE)
    
    # Rank candidates by flight risk drivers (burnout - sentiment - compa_ratio)
    candidate_scores = []
    for e_id in total_active_pool:
        st = emp_state[e_id]
        cur_comp = st["comp_ref"]
        role_mid = roles_by_dept_grade[(st["current_dept"], st["current_grade"])]["mid_salary"]
        compa = cur_comp["base_salary"] / role_mid
        
        # Flight risk weight
        score = (st["latent_burnout"] * 2.0) - (st["latent_sentiment"] * 1.5) + (1.0 - compa)
        candidate_scores.append((e_id, score))
        
    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select voluntary departures from top risk scores + slight random noise
    top_candidates = [cid for cid, _ in candidate_scores[:int(target_vol_count * 1.8)]]
    vol_leavers = set(random.sample(top_candidates, min(target_vol_count, len(top_candidates))))
    
    # Select involuntary departures from low performers
    low_perf_pool = [e_id for e_id, st in emp_state.items() if st["latent_performance"] < 3.2 and e_id not in vol_leavers]
    invol_leavers = set(random.sample(low_perf_pool, min(target_invol_count, len(low_perf_pool)))) if low_perf_pool else set()
    
    # Select retirements from high-tenure or senior staff
    retire_pool = [e_id for e_id, st in emp_state.items() if st["current_grade"] >= 10 and e_id not in vol_leavers and e_id not in invol_leavers]
    retire_leavers = set(random.sample(retire_pool, min(target_retire_count, len(retire_pool)))) if retire_pool else set()
    
    # Process Attrition Events
    all_leavers = list(vol_leavers) + list(invol_leavers) + list(retire_leavers)
    
    for e_id in all_leavers:
        st = emp_state[e_id]
        emp = emp_lookup[e_id]
        
        # Pick separation date strictly after the latest promotion / compensation revision
        latest_event_dt = max(
            st["hire_date"],
            st["comp_ref"]["effective_from"],
            st["hist_ref"]["effective_from"],
            SIMULATION_START_DATE
        )
        remaining_days = (SIMULATION_END_DATE - latest_event_dt).days
        if remaining_days > 20:
            sep_dt = latest_event_dt + timedelta(days=random.randint(15, remaining_days - 2))
        else:
            sep_dt = latest_event_dt + timedelta(days=max(1, remaining_days))
                
        if e_id in vol_leavers:
            sep_type = "VOLUNTARY"
            reason = random.choice(["COMPENSATION", "CAREER_GROWTH", "BETTER_OPPORTUNITY", "WORK_LIFE_BALANCE"])
            notice_days = random.choice([14, 21, 30])
        elif e_id in invol_leavers:
            sep_type = "INVOLUNTARY"
            reason = "PERFORMANCE_SEPARATION"
            notice_days = 0
        else:
            sep_type = "RETIREMENT"
            reason = "NORMAL_RETIREMENT"
            notice_days = 60
            
        # Regret status determination (Rule BR-ATT-02)
        if sep_type == "VOLUNTARY":
            if st["current_grade"] >= 6 or st["latent_performance"] >= 3.8:
                regret = "REGRETTABLE"
            else:
                regret = "NON_REGRETTABLE"
        elif sep_type == "INVOLUNTARY":
            regret = "NON_REGRETTABLE"
        else:
            regret = "UNDETERMINED"
            
        # Update Master Employee State
        emp["status"] = "TERMINATED" if sep_type != "RETIREMENT" else "RETIRED"
        emp["is_active"] = False
        st["is_active"] = False
        st["separation_date"] = sep_dt
        
        # Close SCD2 History and Compensation
        if st["hist_ref"]["effective_to"] is None:
            st["hist_ref"]["effective_to"] = sep_dt
            st["hist_ref"]["is_current"] = False
            
        if st["comp_ref"]["effective_to"] is None:
            st["comp_ref"]["effective_to"] = sep_dt
            st["comp_ref"]["is_current"] = False
            
        exit_records.append({
            "exit_id": generate_deterministic_uuid(),
            "employee_id": e_id,
            "separation_date": sep_dt,
            "separation_type": sep_type,
            "regret_status": regret,
            "primary_reason": reason,
            "secondary_reason": "RELOCATION" if random.random() < 0.2 else None,
            "notice_period_days_served": notice_days,
            "exit_interview_completed": sep_type == "VOLUNTARY" and random.random() < 0.88,
            "would_rehire": sep_type != "INVOLUNTARY",
            "destination_industry": "Direct Competitor" if regret == "REGRETTABLE" else "Other Technology",
        })

    # Return complete simulated longitudinal entities
    return {
        "compensation_records": compensation_records,
        "employee_history": employee_history,
        "performance_evaluations": performance_evaluations,
        "engagement_surveys": engagement_surveys,
        "projects": projects,
        "project_assignments": project_assignments,
        "time_off_records": time_off_records,
        "attrition_risk_scores": attrition_risk_scores,
        "retention_interventions": retention_interventions,
        "exit_records": exit_records,
        "emp_state": emp_state,
    }
