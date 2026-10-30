"""
WorkforceIQ – SHAP Explainability and Interpretability Module (Phase 6).

Provides:
  - Global feature importance via mean absolute SHAP values.
  - Individual employee risk explanations with top positive drivers and negative protective factors.
  - Human-readable feature name mapping and domain interpretations.
  - SHAP summary plot generation persisted to ml/artifacts/shap_summary.png.
  - Responsible AI guardrails and advisory disclaimers on all outputs.

CRITICAL RESPONSIBLE AI MANDATE:
  SHAP values describe statistical associations learned by the model, NOT causal relationships.
  A high SHAP value for a feature does NOT imply that changing that feature will prevent attrition.
  All outputs are advisory retention signals intended strictly for human-led, supportive engagement.
  Automated employment decisions (terminations, promotions, compensation changes) based on these scores
  are strictly prohibited.
"""

import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Set matplotlib cache directory to local scratch folder
SCRATCH_DIR = PROJECT_ROOT / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(SCRATCH_DIR / "matplotlib")

# ---------------------------------------------------------------------------
# Human-Readable Feature Dictionary
# ---------------------------------------------------------------------------

FEATURE_LABEL_MAP: Dict[str, str] = {
    "grade_level": "Job Grade Level",
    "tenure_months": "Tenure (Months)",
    "base_salary": "Base Salary (USD)",
    "compa_ratio": "Compa-Ratio (Salary vs. Market Midpoint)",
    "promotions_count": "Career Velocity (Promotion Count)",
    "avg_job_satisfaction": "Engagement (Average Job Satisfaction)",
    "avg_work_life_balance": "Well-Being (Work-Life Balance Score)",
    "latest_burnout_risk": "Burnout Risk Index",
    "latest_sentiment_score": "Sentiment Score (Surveys & Feedback)",
    "avg_weekly_logged_hours": "Workload Intensity (Average Weekly Hours)",
    "grade_level_missing_indicator": "Grade Level (Missingness Indicator)",
    "tenure_months_missing_indicator": "Tenure (Missingness Indicator)",
    "base_salary_missing_indicator": "Base Salary (Missingness Indicator)",
    "compa_ratio_missing_indicator": "Compa-Ratio (Missingness Indicator)",
    "promotions_count_missing_indicator": "Promotions (Missingness Indicator)",
    "avg_job_satisfaction_missing_indicator": "Job Satisfaction (Missingness Indicator)",
    "avg_work_life_balance_missing_indicator": "Work-Life Balance (Missingness Indicator)",
    "latest_burnout_risk_missing_indicator": "Burnout Risk (Missingness Indicator)",
    "latest_sentiment_score_missing_indicator": "Sentiment (Missingness Indicator)",
    "avg_weekly_logged_hours_missing_indicator": "Weekly Hours (Missingness Indicator)",
    "work_location_HYBRID": "Work Arrangement: Hybrid",
    "work_location_ONSITE": "Work Arrangement: On-Site",
    "work_location_REMOTE": "Work Arrangement: Remote",
    "employment_type_CONTRACTOR": "Employment: Contractor",
    "employment_type_FULL_TIME": "Employment: Full-Time",
    "employment_type_INTERN": "Employment: Intern",
    "employment_type_PART_TIME": "Employment: Part-Time",
}

DEPARTMENT_NAMES: Dict[str, str] = {
    "DEP-ENG-01": "Engineering",
    "DEP-AIR-02": "AI Research",
    "DEP-PRD-03": "Product Management",
    "DEP-SAL-04": "Sales & Accounts",
    "DEP-MKT-05": "Marketing & Growth",
    "DEP-CUS-06": "Customer Success",
    "DEP-PPL-07": "People & HR",
    "DEP-FIN-08": "Finance & Legal",
}

RESPONSIBLE_AI_DISCLAIMER: str = (
    "This flight-risk score and SHAP explanation reflect statistical associations learned from "
    "historical organizational data. They do NOT imply causal attribution. These metrics are advisory "
    "signals designed exclusively to support human-led retention dialogues, workload rebalancing, and "
    "career coaching. Automated employment decisions based on this signal are strictly prohibited."
)


def get_human_label(feature_name: str) -> str:
    """Returns an intuitive, executive-friendly description for a feature name."""
    if feature_name in FEATURE_LABEL_MAP:
        return FEATURE_LABEL_MAP[feature_name]

    # Handle department one-hot indicators
    if feature_name.startswith("department_id_"):
        dept_code = feature_name.replace("department_id_", "")
        dept_name = DEPARTMENT_NAMES.get(dept_code, dept_code)
        return f"Department: {dept_name}"

    # General pattern
    clean = feature_name.replace("_", " ").title()
    return clean


def get_risk_tier(calibrated_probability: float) -> str:
    """
    Maps a well-calibrated prospective voluntary attrition probability to an operational risk tier.
    
    Calibration Context:
      - Baseline quarterly voluntary exit rate is ~1.5%.
      - CRITICAL: >= 0.065 (>7x baseline risk, ~top 1-2% of workforce)
      - HIGH: >= 0.045 to < 0.065 (4-6x baseline risk, ~top 3-7% of workforce)
      - MEDIUM: >= 0.025 to < 0.045 (2-3x baseline risk, ~top 8-22% of workforce)
      - LOW: < 0.025 (< 0.5% empirical departure rate, ~78% of workforce)
    """
    if calibrated_probability >= 0.065:
        return "CRITICAL"
    elif calibrated_probability >= 0.045:
        return "HIGH"
    elif calibrated_probability >= 0.025:
        return "MEDIUM"
    else:
        return "LOW"


def load_model_artifacts() -> Tuple[Any, Any, Any, List[str], Dict[str, Any]]:
    """
    Loads preprocessor, raw classifier, Platt calibrator, feature names, and metadata.
    """
    prep = joblib.load(ARTIFACTS_DIR / "preprocessor.joblib")
    raw_clf = joblib.load(ARTIFACTS_DIR / "raw_classifier.joblib")
    calibrator = joblib.load(ARTIFACTS_DIR / "best_model.joblib")

    with open(ARTIFACTS_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)

    with open(ARTIFACTS_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    feature_names = schema["transformed_feature_names"]
    return prep, raw_clf, calibrator, feature_names, meta


def compute_global_shap_importance(
    X_background: pd.DataFrame,
    n_background_samples: int = 100,
    n_eval_samples: int = 1000,
    random_state: int = 20261022,
) -> Dict[str, Any]:
    """
    Computes global feature importance using SHAP TreeExplainer across background samples.
    """
    import shap

    prep, raw_clf, calibrator, feature_names, meta = load_model_artifacts()

    # Preprocess feature matrix
    X_trans = prep.transform(X_background)

    rng = np.random.default_rng(random_state)
    n_bg = min(n_background_samples, X_trans.shape[0])
    bg_idx = rng.choice(X_trans.shape[0], size=n_bg, replace=False)
    X_bg = X_trans[bg_idx]

    # Subsample evaluation samples for fast, highly accurate global importance estimation
    n_ev = min(n_eval_samples, X_trans.shape[0])
    ev_idx = rng.choice(X_trans.shape[0], size=n_ev, replace=False)
    X_eval = X_trans[ev_idx]

    # TreeExplainer for Random Forest
    explainer = shap.TreeExplainer(raw_clf, data=X_bg, feature_names=feature_names)
    shap_vals = explainer.shap_values(X_eval)

    if isinstance(shap_vals, list):
        shap_matrix = shap_vals[1]  # Voluntary exit class
    elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
        shap_matrix = shap_vals[:, :, 1]
    else:
        shap_matrix = shap_vals

    mean_abs_shap = np.abs(shap_matrix).mean(axis=0).tolist()

    ranked = sorted(
        zip(feature_names, mean_abs_shap),
        key=lambda item: item[1],
        reverse=True,
    )

    ranked_items = [
        {
            "rank": rank + 1,
            "feature": fname,
            "human_label": get_human_label(fname),
            "mean_abs_shap": round(float(val), 6),
            "importance_pct": round(float(val / sum(mean_abs_shap) * 100), 2) if sum(mean_abs_shap) > 0 else 0.0,
        }
        for rank, (fname, val) in enumerate(ranked)
    ]

    return {
        "model_version": meta.get("model_version", "v2.0.0-prospective"),
        "algorithm": meta.get("algorithm", "RandomForest"),
        "total_features": len(feature_names),
        "evaluation_samples": int(X_trans.shape[0]),
        "ranked_features": ranked_items,
        "responsible_ai_disclaimer": RESPONSIBLE_AI_DISCLAIMER,
    }


def compute_individual_explanation(
    employee_id: str,
    X_single: pd.DataFrame,
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Computes individual SHAP risk explanation for an active employee.
    Separates positive risk drivers from protective factors.
    """
    import shap

    prep, raw_clf, calibrator, feature_names, meta = load_model_artifacts()

    X_trans = prep.transform(X_single)

    raw_prob = float(raw_clf.predict_proba(X_trans)[:, 1][0])
    cal_prob = float(calibrator.predict_proba(np.array([[raw_prob]]))[:, 1][0])
    risk_tier = get_risk_tier(cal_prob)

    explainer = shap.TreeExplainer(raw_clf, feature_names=feature_names)
    shap_vals = explainer.shap_values(X_trans)

    if isinstance(shap_vals, list):
        row_shap = shap_vals[1][0]
    elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
        row_shap = shap_vals[0, :, 1]
    else:
        row_shap = shap_vals[0]

    drivers = sorted(
        zip(feature_names, row_shap),
        key=lambda x: x[1],
        reverse=True,
    )

    # Risk drivers (increase attrition risk)
    top_risk_drivers = [
        {
            "feature": fname,
            "human_label": get_human_label(fname),
            "shap_value": round(float(val), 6),
            "direction": "INCREASES_RISK",
            "interpretation": f"{get_human_label(fname)} is contributing positively to estimated flight risk.",
        }
        for fname, val in drivers
        if val > 0
    ][:top_n]

    # Protective factors (decrease attrition risk)
    top_protective_factors = [
        {
            "feature": fname,
            "human_label": get_human_label(fname),
            "shap_value": round(float(val), 6),
            "direction": "DECREASES_RISK",
            "interpretation": f"{get_human_label(fname)} is acting as an active retention stabilizer.",
        }
        for fname, val in reversed(drivers)
        if val < 0
    ][:top_n]

    return {
        "employee_id": employee_id,
        "flight_risk_probability": round(cal_prob, 4),
        "raw_model_score": round(raw_prob, 4),
        "risk_tier": risk_tier,
        "operational_threshold": meta.get("threshold_optimization", {}).get("selected_operational_threshold", 0.050),
        "is_retention_alert": bool(cal_prob >= 0.050),
        "top_risk_drivers": top_risk_drivers,
        "top_protective_factors": top_protective_factors,
        "responsible_ai_disclaimer": RESPONSIBLE_AI_DISCLAIMER,
    }


def generate_shap_summary_plot(
    X_background: pd.DataFrame,
    output_path: Optional[Path] = None,
    n_samples: int = 500,
) -> Path:
    """
    Renders and saves a global SHAP summary plot (bar chart of top feature importances)
    to ml/artifacts/shap_summary.png.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    prep, raw_clf, calibrator, feature_names, _ = load_model_artifacts()

    # Preprocess
    X_trans = prep.transform(X_background)
    rng = np.random.default_rng(20261022)
    n = min(n_samples, X_trans.shape[0])
    idx = rng.choice(X_trans.shape[0], size=n, replace=False)
    X_sub = X_trans[idx]

    import shap
    explainer = shap.TreeExplainer(raw_clf, data=X_sub, feature_names=feature_names)
    shap_vals = explainer.shap_values(X_sub)

    if isinstance(shap_vals, list):
        shap_matrix = shap_vals[1]
    elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
        shap_matrix = shap_vals[:, :, 1]
    else:
        shap_matrix = shap_vals

    mean_abs = np.abs(shap_matrix).mean(axis=0)
    top_indices = np.argsort(mean_abs)[::-1][:15]

    top_names = [get_human_label(feature_names[i]) for i in top_indices][::-1]
    top_values = [mean_abs[i] for i in top_indices][::-1]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(top_names, top_values, color="#1e88e5", edgecolor="#0d47a1", height=0.6)
    ax.set_xlabel("Mean Absolute SHAP Value (Impact on Model Output Magnitude)", fontsize=11, fontweight="bold")
    ax.set_title("WorkforceIQ – Top 15 Global Retention Risk Drivers (SHAP TreeExplainer)", fontsize=13, fontweight="bold", pad=15)
    ax.grid(axis="x", linestyle="--", alpha=0.6)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(
            f"{width:.4f}",
            xy=(width, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    target_path = output_path or (ARTIFACTS_DIR / "shap_summary.png")
    plt.savefig(target_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return target_path


def run_explainability_pipeline() -> None:
    """
    Executes the complete SHAP explainability generation pipeline:
      1. Global feature importance calculation
      2. Summary plot generation
      3. Sample individual explanations (high, medium, low risk)
      4. Artifact persistence
    """
    print("=" * 70)
    print("WorkforceIQ Phase 6 – SHAP Explainability & Interpretability")
    print("=" * 70)

    from ml.features import get_prospective_temporal_splits

    print("\n1. Loading prospective temporal data splits...")
    X_train, y_train, _, X_val, y_val, _, _ = get_prospective_temporal_splits()
    print(f"   Background dataset: {X_train.shape[0]:,} training samples")

    print("\n2. Computing global SHAP feature importance...")
    global_importance = compute_global_shap_importance(X_train)
    with open(ARTIFACTS_DIR / "shap_global_importance.json", "w", encoding="utf-8") as f:
        json.dump(global_importance, f, indent=2)

    print("   Top 10 Global Features by Mean |SHAP|:")
    for item in global_importance["ranked_features"][:10]:
        print(f"     {item['rank']:>2}. {item['human_label']:<45}: {item['mean_abs_shap']:.6f} ({item['importance_pct']:.1f}%)")

    print("\n3. Generating SHAP summary plot...")
    plot_file = generate_shap_summary_plot(X_train)
    print(f"   Saved plot to {plot_file}")

    print("\n4. Generating sample employee explanations across risk tiers...")
    prep, raw_clf, calibrator, _, _ = load_model_artifacts()
    X_val_trans = prep.transform(X_val)
    val_raw = raw_clf.predict_proba(X_val_trans)[:, 1].reshape(-1, 1)
    val_cal = calibrator.predict_proba(val_raw)[:, 1]

    # Select representative samples from different risk tiers
    rng = np.random.default_rng(20261022)
    crit_indices = np.where(val_cal >= 0.065)[0]
    high_indices = np.where((val_cal >= 0.045) & (val_cal < 0.065))[0]
    med_indices = np.where((val_cal >= 0.025) & (val_cal < 0.045))[0]
    low_indices = np.where(val_cal < 0.025)[0]

    selected_idx = []
    if len(crit_indices) > 0:
        selected_idx.extend(rng.choice(crit_indices, size=min(3, len(crit_indices)), replace=False))
    if len(high_indices) > 0:
        selected_idx.extend(rng.choice(high_indices, size=min(3, len(high_indices)), replace=False))
    if len(med_indices) > 0:
        selected_idx.extend(rng.choice(med_indices, size=min(2, len(med_indices)), replace=False))
    if len(low_indices) > 0:
        selected_idx.extend(rng.choice(low_indices, size=min(2, len(low_indices)), replace=False))

    sample_explanations = []
    for idx in selected_idx:
        emp_id = X_val.index[idx].split("_")[0]
        X_row = X_val.iloc[[idx]]
        explanation = compute_individual_explanation(emp_id, X_row)
        sample_explanations.append(explanation)

    with open(ARTIFACTS_DIR / "shap_sample_explanations.json", "w", encoding="utf-8") as f:
        json.dump(sample_explanations, f, indent=2)

    print(f"   Saved {len(sample_explanations)} representative explanations to {ARTIFACTS_DIR / 'shap_sample_explanations.json'}")
    print("\n" + "=" * 70)
    print("SHAP explainability pipeline successfully completed.")
    print("=" * 70)


if __name__ == "__main__":
    run_explainability_pipeline()
