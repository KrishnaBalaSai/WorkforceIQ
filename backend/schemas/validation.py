"""
Pydantic schemas for Data Quality Validation and Manifest Auditing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ValidationIssue(BaseModel):
    pillar_number: int
    pillar_name: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    entity_name: str
    description: str
    record_id: Optional[str] = None
    sample_payload: Optional[Dict[str, Any]] = None


class ValidationPillarResult(BaseModel):
    pillar_name: str
    status: str  # PASSED, FAILED
    total_checks: int
    violations_count: int
    details: Optional[Dict[str, Any]] = None


class ValidationSummaryResponse(BaseModel):
    status: str  # PASSED, FAILED
    evaluated_at: datetime
    total_pillars_evaluated: int
    passed_pillars_count: int
    failed_pillars_count: int
    total_violations_count: int
    pillars: List[ValidationPillarResult] = Field(default_factory=list)
    recent_anomalies: List[Dict[str, Any]] = Field(default_factory=list)

    @computed_field
    @property
    def overall_status(self) -> str:
        """Alias for status to maintain backward compatibility with dashboard consumers."""
        return self.status

    @computed_field
    @property
    def total_pillars(self) -> int:
        """Alias for total_pillars_evaluated to maintain backward compatibility."""
        return self.total_pillars_evaluated

    @computed_field
    @property
    def passed_pillars(self) -> int:
        """Alias for passed_pillars_count to maintain backward compatibility."""
        return self.passed_pillars_count
