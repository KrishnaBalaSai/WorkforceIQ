"""WorkforceIQ API Routes package."""
from backend.routes.attrition import router as attrition_router
from backend.routes.audit import router as audit_router
from backend.routes.departments import router as departments_router
from backend.routes.employees import router as employees_router
from backend.routes.engagement import router as engagement_router
from backend.routes.health import router as health_router
from backend.routes.interventions import router as interventions_router
from backend.routes.predictions import router as predictions_router
from backend.routes.validation import router as validation_router
from backend.routes.workload import router as workload_router
from backend.routes.exports import router as exports_router

__all__ = [
    "attrition_router",
    "audit_router",
    "departments_router",
    "employees_router",
    "engagement_router",
    "health_router",
    "interventions_router",
    "predictions_router",
    "validation_router",
    "workload_router",
    "exports_router",
]
