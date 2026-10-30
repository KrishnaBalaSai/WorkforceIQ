"""
Dataset Exporter for WorkforceIQ Synthetic Workforce Data Generator.
Handles high-performance CSV and JSON exports, separation of ground truth,
and generation of derived feature sets.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

def json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_datasets(
    datasets: Dict[str, List[Dict[str, Any]]],
    anomaly_manifest: List[Dict[str, Any]],
    output_dir: Path,
    export_json: bool = True,
) -> Dict[str, Any]:
    """
    Exports clean input entities, derived feature tables, and separate ground-truth files.
    """
    generated_dir = output_dir / "generated"
    ground_truth_dir = output_dir / "ground_truth"
    manifests_dir = output_dir / "manifests"
    
    generated_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    
    exported_files = []
    
    # -------------------------------------------------------------------------
    # 1. Export Clean Input Relational Tables (data/generated/)
    # -------------------------------------------------------------------------
    clean_tables = [
        "departments", "job_roles", "skills", "employees", "employee_skills",
        "employee_history", "compensation_records", "performance_evaluations",
        "engagement_surveys", "projects", "project_assignments", "time_off_records",
        "attrition_risk_scores", "retention_interventions", "data_anomalies"
    ]
    
    for tbl_name in clean_tables:
        rows = datasets.get(tbl_name, [])
        if not rows:
            continue
            
        df = pd.DataFrame(rows)
        # Drop temporary simulation helper columns if present
        df = df.drop(columns=["grade_level"], errors="ignore")
        
        csv_path = generated_dir / f"{tbl_name}.csv"
        df.to_csv(csv_path, index=False)
        exported_files.append(str(csv_path))
        
        if export_json:
            json_path = generated_dir / f"{tbl_name}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, default=json_serial, indent=2)
            exported_files.append(str(json_path))

    # -------------------------------------------------------------------------
    # 2. Export Ground Truth Datasets Separately (data/ground_truth/)
    # -------------------------------------------------------------------------
    # A. Exit Records
    exit_rows = datasets.get("exit_records", [])
    if exit_rows:
        df_exits = pd.DataFrame(exit_rows)
        csv_exit = ground_truth_dir / "exit_records.csv"
        df_exits.to_csv(csv_exit, index=False)
        exported_files.append(str(csv_exit))
        
        if export_json:
            json_exit = ground_truth_dir / "exit_records.json"
            with open(json_exit, "w", encoding="utf-8") as f:
                json.dump(exit_rows, f, default=json_serial, indent=2)
            exported_files.append(str(json_exit))
            
    # B. Attrition Binary Labels (Strictly separated for ML evaluation)
    vol_exit_ids = {
        ex["employee_id"]: ex for ex in exit_rows if ex.get("separation_type") == "VOLUNTARY"
    }
    attrition_labels = []
    for emp in datasets.get("employees", []):
        e_id = emp["employee_id"]
        is_vol_attrited = e_id in vol_exit_ids
        attrition_labels.append({
            "employee_id": e_id,
            "has_attrited_voluntary": is_vol_attrited,
            "separation_date": vol_exit_ids[e_id]["separation_date"] if is_vol_attrited else None,
            "regret_status": vol_exit_ids[e_id]["regret_status"] if is_vol_attrited else "ACTIVE",
        })
    df_labels = pd.DataFrame(attrition_labels)
    csv_labels = ground_truth_dir / "attrition_labels.csv"
    df_labels.to_csv(csv_labels, index=False)
    exported_files.append(str(csv_labels))

    # C. Anomaly Manifest (Ground Truth for all 4 injected anomaly scenarios)
    if anomaly_manifest:
        df_anom = pd.DataFrame(anomaly_manifest)
        csv_anom = ground_truth_dir / "anomaly_manifest.csv"
        df_anom.to_csv(csv_anom, index=False)
        exported_files.append(str(csv_anom))
        
        if export_json:
            json_anom = ground_truth_dir / "anomaly_manifest.json"
            with open(json_anom, "w", encoding="utf-8") as f:
                json.dump(anomaly_manifest, f, default=json_serial, indent=2)
            exported_files.append(str(json_anom))

    # -------------------------------------------------------------------------
    # 3. Export Derived Features Table (Pre-outcome features only)
    # -------------------------------------------------------------------------
    derived_features = build_derived_features(datasets)
    if derived_features:
        df_derived = pd.DataFrame(derived_features)
        csv_derived = generated_dir / "derived_workforce_features.csv"
        df_derived.to_csv(csv_derived, index=False)
        exported_files.append(str(csv_derived))

    # -------------------------------------------------------------------------
    # 4. Export Generation Manifest & Metrics
    # -------------------------------------------------------------------------
    manifest_data = {
        "generated_at": datetime.now().isoformat(),
        "total_employees": len(datasets.get("employees", [])),
        "total_exit_records": len(exit_rows),
        "total_anomalies_injected": len(anomaly_manifest),
        "anomaly_breakdown": pd.Series(
            [a["anomaly_type"] for a in anomaly_manifest]
        ).value_counts().to_dict() if anomaly_manifest else {},
        "table_row_counts": {k: len(v) for k, v in datasets.items()},
        "exported_file_count": len(exported_files),
    }
    
    manifest_path = manifests_dir / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    exported_files.append(str(manifest_path))

    return {
        "manifest": manifest_data,
        "exported_files": exported_files,
    }

def build_derived_features(datasets: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Computes derived workforce features strictly from pre-outcome source records:
    - Current compa-ratio
    - Total tenure (months)
    - Average engagement score
    - Latest burnout index
    - Total promotions count
    - Average weekly logged hours
    """
    employees = datasets.get("employees", [])
    job_roles = {r["role_id"]: r for r in datasets.get("job_roles", [])}
    comps = datasets.get("compensation_records", [])
    surveys = datasets.get("engagement_surveys", [])
    history = datasets.get("employee_history", [])
    assignments = datasets.get("project_assignments", [])
    
    # Map current compensation
    curr_comp_by_emp = {}
    for c in comps:
        if c.get("is_current") is True:
            curr_comp_by_emp[c["employee_id"]] = c
            
    # Group surveys by emp
    surveys_by_emp = {}
    for s in surveys:
        surveys_by_emp.setdefault(s["employee_id"], []).append(s)
        
    # Group history by emp
    promotions_by_emp = {}
    for h in history:
        if h.get("change_reason") == "PROMOTION":
            promotions_by_emp[h["employee_id"]] = promotions_by_emp.get(h["employee_id"], 0) + 1
            
    # Group project hours by emp
    hours_by_emp = {}
    for p in assignments:
        hours_by_emp.setdefault(p["employee_id"], []).append(p.get("logged_hours_weekly", 40.0))

    ref_date = date(2026, 10, 31)
    derived = []
    
    for emp in employees:
        e_id = emp["employee_id"]
        role = job_roles.get(emp["role_id"], {})
        comp = curr_comp_by_emp.get(e_id, {})
        emp_surveys = surveys_by_emp.get(e_id, [])
        emp_hours = hours_by_emp.get(e_id, [40.0])
        
        # Tenure in months
        hire_dt = emp["hire_date"]
        tenure_months = round((ref_date - hire_dt).days / 30.4375, 1)
        
        # Compa-ratio
        mid = role.get("mid_salary", 1.0)
        base = comp.get("base_salary", mid)
        compa_ratio = round(base / mid, 3) if mid > 0 else 1.0
        
        # Latest and avg survey metrics
        if emp_surveys:
            sorted_surveys = sorted(emp_surveys, key=lambda x: x["survey_date"])
            latest_s = sorted_surveys[-1]
            avg_sat = round(sum(s["job_satisfaction"] for s in emp_surveys) / len(emp_surveys), 2)
            avg_wlb = round(sum(s["work_life_balance"] for s in emp_surveys) / len(emp_surveys), 2)
            latest_burnout = latest_s["burnout_risk_index"]
            latest_sentiment = latest_s["sentiment_score"]
        else:
            avg_sat = 3.5
            avg_wlb = 3.5
            latest_burnout = 0.25
            latest_sentiment = 0.20
            
        avg_logged_hours = round(sum(emp_hours) / len(emp_hours), 2)
        promo_count = promotions_by_emp.get(e_id, 0)
        
        derived.append({
            "employee_id": e_id,
            "department_id": emp["department_id"],
            "role_id": emp["role_id"],
            "grade_level": role.get("grade_level", 1),
            "tenure_months": tenure_months,
            "base_salary": base,
            "compa_ratio": compa_ratio,
            "promotions_count": promo_count,
            "avg_job_satisfaction": avg_sat,
            "avg_work_life_balance": avg_wlb,
            "latest_burnout_risk": latest_burnout,
            "latest_sentiment_score": latest_sentiment,
            "avg_weekly_logged_hours": avg_logged_hours,
        })
        
    return derived
