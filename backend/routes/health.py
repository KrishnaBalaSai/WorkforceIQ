"""
WorkforceIQ – Health Check Routes.
GET /health        : Liveness probe with DB + CSV status.
GET /health/ready  : Readiness probe verifying DB connectivity.
"""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.database import check_database_health
from backend.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns service health including database connectivity and CSV fallback status.",
)
def liveness():
    info = check_database_health()
    status = "healthy" if info.get("postgresql_reachable") or info.get("csv_fallback_available") else "degraded"
    return HealthResponse(
        status=status,
        version="1.0.0",
        database_type=info.get("database_type", "unknown"),
        db_url_configured=info.get("db_url_configured", False),
        postgresql_reachable=info.get("postgresql_reachable", False),
        csv_fallback_available=info.get("csv_fallback_available", False),
        csv_files_found=info.get("csv_files_found", 0),
        timestamp=datetime.now(),
    )


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Returns 200 if PostgreSQL is reachable, 503 otherwise.",
)
def readiness():
    info = check_database_health()
    if info.get("postgresql_reachable"):
        return {"status": "ready", "database": "postgresql", "timestamp": datetime.now().isoformat()}
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "reason": info.get("postgresql_error", "PostgreSQL unreachable"),
            "csv_fallback": info.get("csv_fallback_available", False),
        },
    )
