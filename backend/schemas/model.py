"""
Pydantic schemas for Machine Learning Models, Evaluation Metrics, and Explainability.
"""

from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FeatureDriver(BaseModel):
    feature_name: str
    feature_value: Optional[float] = None
    shap_value: float
    direction: str  # INCREASES_RISK, DECREASES_RISK
    human_explanation: str


class ModelExplanation(BaseModel):
    employee_id: str
    prediction_date: date
    flight_risk_prob: float = Field(ge=0.0, le=1.0)
    risk_tier: str  # LOW, MEDIUM, HIGH, CRITICAL
    model_version: str
    drivers: List[FeatureDriver] = Field(default_factory=list)
    confidence_interval: Optional[Dict[str, float]] = None
    fairness_disclaimer: str = (
        "This score is an advisory retention signal for supportive human-led "
        "engagement conversations and must NOT be used for automated employment decisions."
    )


class ModelMetrics(BaseModel):
    model_version: str
    algorithm: str
    trained_at: str
    evaluation_split: str  # TEST
    sample_count: int
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    pr_auc: float
    brier_score: Optional[float] = None
    feature_importance: List[Dict[str, float]] = Field(default_factory=list)
    responsible_ai_checks: Dict[str, bool] = Field(default_factory=dict)
