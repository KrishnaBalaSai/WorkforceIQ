"""
WorkforceIQ – Main FastAPI Application Entrypoint (Phase 5).

AI-Powered Workforce Retention Intelligence Platform.
Provides RESTful APIs for Employee 360, Department & Role Analytics,
Longitudinal Engagement & Workload Intelligence, Retention Interventions
with Human-in-the-Loop Governance, Data Quality Validation, and Audit Logging.
"""

from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.database import check_database_health
from backend.routes import (
    attrition_router,
    audit_router,
    departments_router,
    employees_router,
    engagement_router,
    health_router,
    interventions_router,
    predictions_router,
    validation_router,
    workload_router,
    exports_router,
)

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("workforceiq.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Validates database health and readiness on startup.
    """
    logger.info("Starting WorkforceIQ REST API...")
    health = check_database_health()
    logger.info("Initial Database Health Check: %s", health)
    yield
    logger.info("Shutting down WorkforceIQ REST API...")


app = FastAPI(
    title="WorkforceIQ API",
    description=(
        "Enterprise AI-Powered Workforce Retention Intelligence Platform. "
        "Provides longitudinal analytics, flight risk intelligence, Responsible AI safeguards, "
        "human-in-the-loop intervention governance, and 12-pillar data validation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS Configuration
origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_log_header(request: Request, call_next):
    """
    Middleware that computes response execution time and logs requests.
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    logger.info(
        "%s %s - %d (%.4fs)",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


# ---------------------------------------------------------------------------
# Centralized Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handles domain validation errors as 422 Unprocessable Entity."""
    logger.warning("Validation error on %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc), "error_type": "ValueError"},
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    """Handles access control / ground-truth isolation breaches as 403 Forbidden."""
    logger.warning("Permission denied on %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc), "error_type": "PermissionError"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Custom format for request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "error_type": "RequestValidationError"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors and returns standardized 500 JSON without leaking secrets."""
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact the WorkforceIQ administrator.",
            "error_type": type(exc).__name__,
        },
    )


# ---------------------------------------------------------------------------
# Root & Information Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/",
    tags=["Root"],
    summary="Platform metadata",
    description="Returns platform identification, status, and navigation links.",
)
def root() -> Dict[str, str]:
    return {
        "service": "WorkforceIQ – AI-Powered Workforce Retention Intelligence Platform",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
    }


# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

# System Health
app.include_router(health_router)

# Core Operational APIs (v1)
app.include_router(employees_router)
app.include_router(departments_router)
app.include_router(attrition_router)
app.include_router(predictions_router)
app.include_router(engagement_router)
app.include_router(workload_router)
app.include_router(interventions_router)
app.include_router(validation_router)
app.include_router(audit_router)
app.include_router(exports_router)
