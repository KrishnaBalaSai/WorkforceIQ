"""
WorkforceIQ – Machine Learning Flight-Risk Predictions and Explainability Routes.

Endpoints:
  GET /api/v1/predictions/{employee_id}         – Real-time employee flight-risk score & SHAP drivers
  GET /api/v1/predictions/model/metrics         – Model metadata, prospective CV, validation & holdout metrics
  GET /api/v1/predictions/model/feature-importance – Global SHAP feature importance rankings
  GET /api/v1/predictions/model/calibration     – Probability calibration report, Brier score vs prior, ECE
"""

from datetime import date
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.schemas.predictions import (
    CalibrationDiagnosticsResponse,
    EmployeePredictionResponse,
    GlobalFeatureImportanceResponse,
)
from backend.services.prediction_service import (
    get_calibration_report,
    get_feature_importance,
    get_model_metadata,
    predict_employee_risk,
)

router = APIRouter(prefix="/api/v1/predictions", tags=["ML Predictions & Explainability"])


@router.get(
    "/model/metrics",
    response_model=Dict[str, Any],
    summary="Model evaluation and performance metrics",
    description=(
        "Returns prospective temporal evaluation results for the operational retention model: "
        "time-aware expanding-window cross-validation, prospective validation cohort comparison, "
        "Platt calibration parameters, validation-only threshold tuning, and blind holdout test set results."
    ),
)
def model_metrics():
    try:
        return get_model_metadata()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/model/feature-importance",
    response_model=GlobalFeatureImportanceResponse,
    summary="Global SHAP feature importance rankings",
    description=(
        "Returns executive-friendly global retention risk drivers ranked by mean absolute SHAP value. "
        "Includes percentage contributions and human-readable interpretations. "
        "Reflects statistical associations, NOT causal conclusions."
    ),
)
def feature_importance():
    try:
        return get_feature_importance()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/model/calibration",
    response_model=CalibrationDiagnosticsResponse,
    summary="Probability calibration quality diagnostics",
    description=(
        "Returns Brier score comparisons against dummy prior baselines, Expected Calibration Error (ECE), "
        "reliability diagram bin distributions, and validation-only threshold optimization table."
    ),
)
def calibration_report():
    try:
        return get_calibration_report()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/{employee_id}",
    response_model=EmployeePredictionResponse,
    summary="Employee flight-risk score and individual SHAP drivers",
    description=(
        "Computes real-time prospective flight-risk probability, empirical risk tier, "
        "and individual SHAP explanation (top positive risk drivers and negative protective factors) "
        "for an active employee using strictly pre-outcome point-in-time features. "
        "Zero ground-truth or separation outcome data is used."
    ),
)
def employee_prediction(
    employee_id: str,
    as_of_date: Optional[date] = Query(
        default=None,
        description="Temporal point-in-time date for feature extraction (defaults to latest snapshot 2026-06-15).",
    ),
    top_n_drivers: int = Query(
        default=5,
        ge=1,
        le=15,
        description="Number of top positive and negative SHAP drivers to return.",
    ),
    session: Session = Depends(get_session),
):
    try:
        return predict_employee_risk(
            session=session,
            employee_id=employee_id,
            as_of_date=as_of_date,
            top_n_drivers=top_n_drivers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error for employee {employee_id}: {str(exc)}",
        )
