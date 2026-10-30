"""
Pydantic schemas for System Audit Logging.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AuditRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    table_name: str
    record_id: str
    action: str  # INSERT, UPDATE, DELETE, STATE_TRANSITION
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    actor_id: str
    client_ip: Optional[str] = None
    recorded_at: datetime
