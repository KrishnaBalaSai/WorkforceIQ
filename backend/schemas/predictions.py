"""
WorkforceIQ – Prediction and Explainability API Schemas (Phase 6).
"""

from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SHAPDriverItem(BaseModel):
    feature: str
    human_label: str
    shap_value: float
    direction: str  # INCREASES_RISK, DECREASES_RISK
    interpretation: str


class EmployeePredictionResponse(BaseModel):
    employee_id: str
    prediction_date: str
    model_version: str
    flight_risk_probability: float = Field(ge=0.0, le=1.0)
    raw_model_score: float = Field(ge=0.0, le=1.0)
    risk_tier: str  # LOW, MEDIUM, HIGH, CRITICAL
    operational_threshold: float
    is_retention_alert: bool
    top_risk_drivers: List[SHAPDriverItem] = Field(default_factory=list)
    top_protective_factors: List[SHAPDriverItem] = Field(default_factory=list)
    responsible_ai_disclaimer: str


class RankedFeatureItem(BaseModel):
    rank: int
    feature: str
    human_label: str
    mean_abs_shap: float
    importance_pct: float


class GlobalFeatureImportanceResponse(BaseModel):
    model_version: str
    algorithm: str
    total_features: int
    evaluation_samples: int
    ranked_features: List[RankedFeatureItem] = Field(default_factory=list)
    responsible_ai_disclaimer: str


class ReliabilityBinItem(BaseModel):
    bin_range: str
    sample_count: int
    mean_predicted_prob: float
    observed_event_rate: float
    absolute_calibration_gap: float


class CalibrationDiagnosticsResponse(BaseModel):
    report_generated_at: str
    methodology: str
    validation_calibration: Dict[str, Any]
    test_calibration: Dict[str, Any]
    threshold_selection: Dict[str, Any]
