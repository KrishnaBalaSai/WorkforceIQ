"""Common shared Pydantic schemas."""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int = Field(description="Total records matching the filter")
    page: int = Field(description="Current page (1-indexed)")
    page_size: int = Field(description="Records per page")
    pages: int = Field(description="Total number of pages")
    data: List[T]


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database_type: str
    db_url_configured: bool
    postgresql_reachable: bool
    csv_fallback_available: bool
    csv_files_found: int
    timestamp: datetime
