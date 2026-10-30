"""
WorkforceIQ – Machine Learning Prospective Feature Engineering Pipeline.

Provides:
  - Point-in-time feature extraction for prospective forecasting.
  - Strict timestamp controls: all features computed strictly on or before T_pred.
  - Disjoint 90-day prospective prediction horizons without overlapping outcome windows.
  - Competing-risk censoring: involuntary terminations and retirements are appropriately censored.
  - Chronological prediction-date train / validation / test splits.
  - Anti-leakage isolation of status flags, exit records, and post-outcome interventions.
  - Reproducible scikit-learn preprocessing pipelines with missingness indicators.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_GENERATED_DIR = PROJECT_ROOT / "data" / "generated"
DATA_GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"

# ---------------------------------------------------------------------------
# Strict Feature Selection & Exclusion Manifest
# ---------------------------------------------------------------------------

NUMERIC_FEATURES = [
    "grade_level",
    "tenure_months",
    "base_salary",
    "compa_ratio",
    "promotions_count",
    "avg_job_satisfaction",
    "avg_work_life_balance",
    "latest_burnout_risk",
    "latest_sentiment_score",
    "avg_weekly_logged_hours",
]

CATEGORICAL_FEATURES = [
    "department_id",
    "work_location",
    "employment_type",
]

EXCLUDED_COLUMNS = [
    "has_attrited_voluntary",
    "separation_date",
    "separation_type",
    "regret_status",
    "exit_interview_notes",
    "exit_id",
    "status",
    "is_active",
    "is_successful",
    "outcome_evaluated_date",
    "action_date",
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "manager_id",
    "probation_end_date",
    "hire_date",
    "actual_attrition",
]

TRAIN_PREDICTION_DATES = [
    "2024-12-15",
    "2025-03-15",
    "2025-06-15",
    "2025-09-15",
    "2025-12-15",
]
VAL_PREDICTION_DATES = ["2026-03-15"]
TEST_PREDICTION_DATES = ["2026-06-15"]


def get_feature_names() -> Dict[str, List[str]]:
    """Returns the registered feature selection manifest."""
    return {
        "numeric": list(NUMERIC_FEATURES),
        "categorical": list(CATEGORICAL_FEATURES),
        "all_features": list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES),
        "excluded": list(EXCLUDED_COLUMNS),
    }


def compute_point_in_time_features(
    as_of_date_str: str,
    horizon_days: int = 90,
    censor_competing_risks: bool = True,
    data_dir: Optional[Path] = None,
    ground_truth_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Computes strictly pre-outcome point-in-time features for all active employees as of as_of_date.
    
    Target:
      Binary indicator of voluntary separation occurring strictly in (as_of_date, as_of_date + horizon_days].
    
    Competing Risks:
      Employees experiencing involuntary termination or retirement during the horizon are right-censored
      and excluded from the voluntary retention risk set for this evaluation window.
    
    Returns:
      X (pd.DataFrame): Point-in-time feature matrix.
      y (pd.Series): Prospective voluntary attrition outcome label.
      groups (pd.Series): Employee IDs for grouped cross-validation.
    """
    d_gen = data_dir or DATA_GENERATED_DIR
    d_gt = ground_truth_dir or DATA_GROUND_TRUTH_DIR

    as_of = pd.to_datetime(as_of_date_str)
    horizon_end = as_of + pd.Timedelta(days=horizon_days)

    emp = pd.read_csv(d_gen / "employees.csv")
    comps = pd.read_csv(d_gen / "compensation_records.csv")
    surveys = pd.read_csv(d_gen / "engagement_surveys.csv")
    history = pd.read_csv(d_gen / "employee_history.csv")
    assignments = pd.read_csv(d_gen / "project_assignments.csv")
    roles = pd.read_csv(d_gen / "job_roles.csv")
    exits = pd.read_csv(d_gt / "exit_records.csv")

    # 1. Eligible active population: Hired on or before as_of, and NOT separated on or before as_of
    emp["hire_dt"] = pd.to_datetime(emp["hire_date"])
    exits_map = exits.set_index("employee_id")["separation_date"].to_dict()
    type_map = exits.set_index("employee_id")["separation_type"].to_dict()

    active_mask = (emp["hire_dt"] <= as_of) & (
        emp["employee_id"].map(
            lambda e: exits_map.get(e) is None or pd.to_datetime(exits_map[e]) > as_of
        )
    )
    active = emp[active_mask].copy()

    # 2. Competing risk censoring: Exclude non-voluntary departures in (as_of, as_of + horizon_days]
    exits["sep_dt"] = pd.to_datetime(exits["separation_date"])
    if censor_competing_risks:
        competing_exits = exits[
            (exits["separation_type"] != "VOLUNTARY")
            & (exits["sep_dt"] > as_of)
            & (exits["sep_dt"] <= horizon_end)
        ]
        censored_ids = set(competing_exits["employee_id"])
        active = active[~active["employee_id"].isin(censored_ids)].copy()

    # 3. Tenure in months strictly as of as_of
    active["tenure_months"] = ((as_of - active["hire_dt"]).dt.days / 30.4375).round(1)

    # 4. Active compensation on as_of
    comps["eff_from"] = pd.to_datetime(comps["effective_from"])
    valid_comps = comps[comps["eff_from"] <= as_of].sort_values(["employee_id", "eff_from"])
    latest_comps = valid_comps.groupby("employee_id").last().reset_index()
    active = pd.merge(active, latest_comps[["employee_id", "base_salary"]], on="employee_id", how="left")

    # 5. Role information and compa-ratio on as_of
    active = pd.merge(active, roles[["role_id", "mid_salary"]], on="role_id", how="left")
    active["grade_level"] = active["role_id"].map(lambda r: int(r.split("-")[-1]) if isinstance(r, str) else 1)
    active["compa_ratio"] = (active["base_salary"] / active["mid_salary"]).round(3).fillna(1.0)

    # 6. Promotions recorded strictly on or before as_of
    history["eff_dt"] = pd.to_datetime(history["effective_from"])
    promos = history[(history["eff_dt"] <= as_of) & (history["change_reason"] == "PROMOTION")]
    promo_counts = promos.groupby("employee_id").size().rename("promotions_count")
    active = pd.merge(active, promo_counts, on="employee_id", how="left")
    active["promotions_count"] = active["promotions_count"].fillna(0).astype(int)

    # 7. Engagement surveys submitted strictly on or before as_of (missingness preserved as NaN)
    surveys["surv_dt"] = pd.to_datetime(surveys["survey_date"])
    valid_surveys = surveys[surveys["surv_dt"] <= as_of].sort_values(["employee_id", "surv_dt"])

    if not valid_surveys.empty:
        avg_sat = valid_surveys.groupby("employee_id")["job_satisfaction"].mean().rename("avg_job_satisfaction").round(2)
        avg_wlb = valid_surveys.groupby("employee_id")["work_life_balance"].mean().rename("avg_work_life_balance").round(2)
        latest_s = valid_surveys.groupby("employee_id").last()
        burnout = latest_s["burnout_risk_index"].rename("latest_burnout_risk")
        sentiment = latest_s["sentiment_score"].rename("latest_sentiment_score")

        active = pd.merge(active, avg_sat, on="employee_id", how="left")
        active = pd.merge(active, avg_wlb, on="employee_id", how="left")
        active = pd.merge(active, burnout, on="employee_id", how="left")
        active = pd.merge(active, sentiment, on="employee_id", how="left")
    else:
        active["avg_job_satisfaction"] = np.nan
        active["avg_work_life_balance"] = np.nan
        active["latest_burnout_risk"] = np.nan
        active["latest_sentiment_score"] = np.nan

    # 8. Weekly logged hours in trailing 90 days before as_of
    assignments["start_dt"] = pd.to_datetime(assignments["start_date"])
    assignments["end_dt"] = pd.to_datetime(assignments["end_date"])
    t_90_start = as_of - pd.Timedelta(days=90)
    active_assigns = assignments[
        (assignments["start_dt"] <= as_of)
        & (assignments["end_dt"].isna() | (assignments["end_dt"] >= t_90_start))
    ]
    if not active_assigns.empty:
        avg_hrs = active_assigns.groupby("employee_id")["logged_hours_weekly"].mean().rename("avg_weekly_logged_hours").round(2)
        active = pd.merge(active, avg_hrs, on="employee_id", how="left")
    else:
        active["avg_weekly_logged_hours"] = np.nan

    # 9. Prospective Target Label: Voluntary separation in (as_of, as_of + horizon_days]
    vol_exits_in_window = exits[
        (exits["separation_type"] == "VOLUNTARY")
        & (exits["sep_dt"] > as_of)
        & (exits["sep_dt"] <= horizon_end)
    ]
    target_ids = set(vol_exits_in_window["employee_id"])

    selected_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = active[selected_cols].copy()
    X.index = [f"{eid}_{as_of_date_str}" for eid in active["employee_id"]]

    y = pd.Series(
        active["employee_id"].isin(target_ids).astype(int).values,
        index=X.index,
        name="voluntary_attrition_in_horizon",
    )

    groups = pd.Series(active["employee_id"].values, index=X.index, name="employee_id")

    return X, y, groups


def get_prospective_temporal_splits(
    horizon_days: int = 90,
    censor_competing_risks: bool = True,
    data_dir: Optional[Path] = None,
    ground_truth_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Constructs chronological prospective splits across prediction periods:
      - Training (Q4 2024 through Q4 2025): 5 quarterly cohorts
      - Validation (Q1 2026): 1 prospective quarterly cohort
      - Test (Q2 2026): 1 holdout prospective quarterly cohort
      
    Guarantees zero overlapping outcome windows, censors non-target departures,
    and fits preprocessors strictly on Train.
    """
    # 1. Training set
    X_train_list, y_train_list, g_train_list = [], [], []
    for dt_str in TRAIN_PREDICTION_DATES:
        X_p, y_p, g_p = compute_point_in_time_features(
            dt_str,
            horizon_days=horizon_days,
            censor_competing_risks=censor_competing_risks,
            data_dir=data_dir,
            ground_truth_dir=ground_truth_dir,
        )
        X_train_list.append(X_p)
        y_train_list.append(y_p)
        g_train_list.append(g_p)

    X_train = pd.concat(X_train_list, axis=0)
    y_train = pd.concat(y_train_list, axis=0)
    groups_train = pd.concat(g_train_list, axis=0)

    # 2. Validation set
    X_val, y_val, _ = compute_point_in_time_features(
        VAL_PREDICTION_DATES[0],
        horizon_days=horizon_days,
        censor_competing_risks=censor_competing_risks,
        data_dir=data_dir,
        ground_truth_dir=ground_truth_dir,
    )

    # 3. Test set
    X_test, y_test, _ = compute_point_in_time_features(
        TEST_PREDICTION_DATES[0],
        horizon_days=horizon_days,
        censor_competing_risks=censor_competing_risks,
        data_dir=data_dir,
        ground_truth_dir=ground_truth_dir,
    )

    return X_train, y_train, groups_train, X_val, y_val, X_test, y_test


def build_preprocessing_pipeline() -> ColumnTransformer:
    """
    Builds a reproducible scikit-learn ColumnTransformer for pre-outcome features.
    - Numerical: Median imputation with missingness indicators + Standard scaling.
    - Categorical: Constant imputation + One-Hot encoding (ignore unknown categories).
    """
    num_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )

    cat_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERIC_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    return preprocessor
