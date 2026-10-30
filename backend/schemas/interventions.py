"""
Pydantic schemas for Retention Interventions and Human-in-the-Loop Lifecycle.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InterventionEventRecord(BaseModel):
    """Immutable audit trail of an intervention status transition."""
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    intervention_id: str
    from_status: Optional[str] = None
    to_status: str
    actor: str
    notes: Optional[str] = None
    recorded_at: datetime


class InterventionCreate(BaseModel):
    """Payload to propose a supportive retention conversation/intervention."""
    employee_id: str = Field(description="Target employee ID")
    risk_score_id: Optional[str] = Field(None, description="Associated prediction risk score ID")
    intervention_type: str = Field(description="Supportive retention intervention type")
    cost_usd: float = Field(0.0, ge=0.0, description="Estimated budget/cost in USD")
    proposed_date: date = Field(default_factory=date.today)
    hr_notes: Optional[str] = Field(None, description="Contextual recommendation and human rationale")


class InterventionStatusPatch(BaseModel):
    """Payload to transition the lifecycle status of an intervention."""
    target_status: str = Field(
        description="Target status: PENDING_REVIEW, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED"
    )
    actor_id: str = Field(description="Human reviewer or system operator ID")
    reviewer_notes: Optional[str] = Field(None, description="Mandatory notes or justification for approval/cancellation")
    action_date: Optional[date] = Field(None, description="Date action was initiated (for IN_PROGRESS)")
    outcome_evaluated_date: Optional[date] = Field(None, description="Date outcome was evaluated (for COMPLETED)")
    is_successful: Optional[bool] = Field(None, description="Post-intervention outcome assessment")


class InterventionRecord(BaseModel):
    """Complete representation of a retention intervention with lifecycle history."""
    model_config = ConfigDict(from_attributes=True)

    intervention_id: str
    employee_id: str
    employee_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    risk_score_id: Optional[str] = None
    intervention_type: str
    status: str
    cost_usd: float
    proposed_date: date
    action_date: Optional[date] = None
    outcome_evaluated_date: Optional[date] = None
    is_successful: Optional[bool] = None
    hr_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    events: List[InterventionEventRecord] = Field(default_factory=list)
