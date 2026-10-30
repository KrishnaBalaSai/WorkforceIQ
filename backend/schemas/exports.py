"""
WorkforceIQ – Data Export and Reporting Schemas (Phase 8).

Defines Pydantic models for:
  - Export metadata, manifests, and checksums.
  - JSON and CSV structured export payloads.
  - Downloadable executive and functional reports.
  - Granular dataset export parameters and filters.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExportManifest(BaseModel):
    """Metadata attached to every data export."""
    dataset_name: str = Field(description="Name of the exported dataset")
    export_format: str = Field(description="Format of the export: csv or json")
    record_count: int = Field(description="Number of records included in the export")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of export generation")
    source: str = Field(default="WorkforceIQ Operational Platform", description="Originating service/database")
    sha256_checksum: str = Field(description="SHA-256 hash of the exported payload bytes")
    parameters_applied: Dict[str, Any] = Field(default_factory=dict, description="Query filters applied during export")
    data_classification: str = Field(default="OPERATIONAL_CONFIDENTIAL", description="Data sensitivity classification")
    responsible_ai_notice: str = Field(
        default="Statistical data for human managerial discretion only. Automated employment decisions strictly prohibited.",
        description="Ethics and governance disclaimer",
    )


class ExportEnvelope(BaseModel):
    """Standard JSON wrapper for operational data exports."""
    manifest: ExportManifest
    data: List[Dict[str, Any]]


class ExecutiveReportData(BaseModel):
    """Structured executive report payload."""
    report_title: str
    generated_at: datetime
    active_headcount: int
    prospective_mean_risk: float
    retention_alerts_count: int
    retention_alerts_pct: float
    validation_status: str
    departments_summary: List[Dict[str, Any]]
    key_retention_drivers: List[Dict[str, float]]
    governance_notes: str
