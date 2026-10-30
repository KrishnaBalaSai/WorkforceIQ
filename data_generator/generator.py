"""
Master WorkforceIQ Synthetic Data Generation Pipeline.
Orchestrates demographic generation, longitudinal simulation, anomaly injection,
validation checks, and dataset export.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any

from data_generator.config import (
    RANDOM_SEED,
    STARTER_EMPLOYEE_COUNT,
    FULL_EMPLOYEE_COUNT,
)
from data_generator.demographics import generate_core_demographics
from data_generator.longitudinal import simulate_workforce_history
from data_generator.anomalies import inject_anomalies
from data_generator.validator import validate_dataset
from data_generator.exporter import export_datasets

def run_pipeline(
    employee_count: int = STARTER_EMPLOYEE_COUNT,
    seed: int = RANDOM_SEED,
    output_dir: Path = None,
    export_json: bool = True,
    inject_negative_scenarios: bool = True,
) -> Dict[str, Any]:
    """
    Executes the end-to-end data generation pipeline.
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent / "data"
        
    starter_mode = employee_count < 1000
    
    print("=" * 70)
    print(" WORKFORCE RETENTION INTELLIGENCE (WorkforceIQ) DATA GENERATOR")
    print(f" Target Cohort Size: {employee_count:,} Employees")
    print(f" Simulation Horizon: 24 Months")
    print(f" Random Seed:        {seed}")
    print(f" Starter Mode:       {starter_mode}")
    print("=" * 70)
    
    # 1. Generate Parent Catalogs & Core Demographics
    print("\n[Step 1/5] Generating Parent Catalogs and Core Demographics...")
    demographics = generate_core_demographics(employee_count)
    print(f"  -> Departments: {len(demographics['departments'])}")
    print(f"  -> Job Roles:   {len(demographics['job_roles'])}")
    print(f"  -> Skills:      {len(demographics['skills'])}")
    print(f"  -> Employees:   {len(demographics['employees'])}")
    print(f"  -> Skills Map:  {len(demographics['employee_skills'])}")

    # 2. Simulate Longitudinal History (24 Months)
    print("\n[Step 2/5] Simulating 24-Month Longitudinal Event History...")
    longitudinal = simulate_workforce_history(demographics)
    print(f"  -> Compensation Records:    {len(longitudinal['compensation_records']):,}")
    print(f"  -> Performance Evaluations: {len(longitudinal['performance_evaluations']):,}")
    print(f"  -> Engagement Surveys:      {len(longitudinal['engagement_surveys']):,}")
    print(f"  -> Project Assignments:     {len(longitudinal['project_assignments']):,}")
    print(f"  -> Time Off Records:        {len(longitudinal['time_off_records']):,}")
    print(f"  -> Attrition Risk Scores:   {len(longitudinal['attrition_risk_scores']):,}")
    print(f"  -> Interventions:           {len(longitudinal['retention_interventions']):,}")
    print(f"  -> Exit Records:            {len(longitudinal['exit_records']):,}")

    # Combine datasets
    all_datasets = {
        "departments": demographics["departments"],
        "job_roles": demographics["job_roles"],
        "skills": demographics["skills"],
        "employees": demographics["employees"],
        "employee_skills": demographics["employee_skills"],
        "employee_history": longitudinal["employee_history"],
        "compensation_records": longitudinal["compensation_records"],
        "performance_evaluations": longitudinal["performance_evaluations"],
        "engagement_surveys": longitudinal["engagement_surveys"],
        "projects": longitudinal["projects"],
        "project_assignments": longitudinal["project_assignments"],
        "time_off_records": longitudinal["time_off_records"],
        "attrition_risk_scores": longitudinal["attrition_risk_scores"],
        "retention_interventions": longitudinal["retention_interventions"],
        "exit_records": longitudinal["exit_records"],
    }

    # 3. Labelled Anomaly Injection
    anomaly_manifest = []
    if inject_negative_scenarios:
        print("\n[Step 3/5] Injecting Labelled Negative Anomaly Scenarios (4 Types)...")
        longitudinal, anomaly_manifest = inject_anomalies(
            demographics, longitudinal, starter_mode=starter_mode
        )
        print(f"  -> Total Injected Anomalies: {len(anomaly_manifest)}")
        for a_type in ["POST_TERMINATION_ACTIVITY", "CIRCULAR_HIERARCHY", "COMPENSATION_INVERSION", "LEAVE_HOUR_CONFLICT"]:
            count = sum(1 for a in anomaly_manifest if a["anomaly_type"] == a_type)
            print(f"     - {a_type}: {count}")

        # Update combined datasets with any newly appended records
        all_datasets["project_assignments"] = longitudinal["project_assignments"]
        all_datasets["engagement_surveys"] = longitudinal["engagement_surveys"]
        all_datasets["compensation_records"] = longitudinal["compensation_records"]
        
        # Populate data_anomalies table
        all_datasets["data_anomalies"] = [
            {
                "anomaly_id": a["anomaly_id"],
                "anomaly_type": a["anomaly_type"],
                "severity": a["severity"],
                "entity_type": a["entity_type"],
                "entity_id": a["entity_id"],
                "description": a["description"],
                "detected_at": a["detected_at"],
                "is_resolved": False,
            }
            for a in anomaly_manifest
        ]
    else:
        all_datasets["data_anomalies"] = []

    # 4. In-Memory Validation Engine
    print("\n[Step 4/5] Executing Schema, Foreign Key & Invariant Validation...")
    val_report = validate_dataset(all_datasets)
    
    print(f"  -> Validation Status: {'PASSED' if val_report['is_valid'] else 'FAILED'}")
    print(f"  -> Errors:            {val_report['error_count']}")
    print(f"  -> Warnings:          {val_report['warning_count']}")
    print(f"  -> Voluntary Attrition Rate: {val_report['statistics'].get('voluntary_attrition_rate_pct', 0.0)}% (Target: 5-15%)")
    
    if val_report["errors"]:
        print("\n[ERROR DETAILS]")
        for err in val_report["errors"][:10]:
            print(f"  ! {err}")
        if not starter_mode:
            sys.exit(1)

    # 5. Export Clean Datasets & Ground Truth Files
    print("\n[Step 5/5] Exporting CSV and JSON Artifacts...")
    export_result = export_datasets(
        all_datasets, anomaly_manifest, output_dir, export_json=export_json
    )
    print(f"  -> Successfully exported {len(export_result['exported_files'])} files.")
    print(f"  -> Output Directory: {output_dir}")
    print("=" * 70)
    print(" PIPELINE EXECUTION COMPLETED")
    print("=" * 70)

    return {
        "datasets": all_datasets,
        "anomaly_manifest": anomaly_manifest,
        "validation_report": val_report,
        "export_result": export_result,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WorkforceIQ Synthetic Data Generator")
    parser.add_argument("--starter", action="store_true", help="Generate starter cohort (150 employees)")
    parser.add_argument("--full", action="store_true", help="Generate full cohort (10,000 employees)")
    parser.add_argument("--count", type=int, default=None, help="Explicit employee count")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    parser.add_argument("--no-json", action="store_true", help="Skip JSON export for speed")
    
    args = parser.parse_args()
    
    count = STARTER_EMPLOYEE_COUNT
    if args.full:
        count = FULL_EMPLOYEE_COUNT
    elif args.starter:
        count = STARTER_EMPLOYEE_COUNT
    elif args.count:
        count = args.count
        
    run_pipeline(
        employee_count=count,
        seed=args.seed,
        export_json=not args.no_json,
    )
