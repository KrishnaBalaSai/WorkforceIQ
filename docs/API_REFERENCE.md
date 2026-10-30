# WorkforceIQ – REST API Specification & Reference

**Base URL:** `http://localhost:8000`  
**API Version:** `v1` (`/api/v1`)  
**Specification Standard:** OpenAPI 3.1.0 (Interactive docs at `http://localhost:8000/docs` and `http://localhost:8000/redoc`)  
**Total Registered Routes:** 48 routes across 10 functional domains  

---

## 1. System Health & Diagnostics

### `GET /`
- **Summary:** Root platform status and navigation index.
- **Response:** `200 OK`
  ```json
  {
    "platform": "WorkforceIQ",
    "version": "1.0.0",
    "status": "operational",
    "documentation": "/docs"
  }
  ```

### `GET /health`
- **Summary:** Service liveness probe reporting PostgreSQL and CSV fallback status.
- **Response:** `200 OK`
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database_type": "postgresql",
    "db_url_configured": true,
    "postgresql_reachable": true,
    "csv_fallback_available": true,
    "csv_files_found": 16,
    "timestamp": "2026-10-30T20:42:00"
  }
  ```

### `GET /health/ready`
- **Summary:** Service readiness probe. Returns 200 if PostgreSQL is actively reachable, 503 otherwise.
- **Response:** `200 OK`
  ```json
  {
    "status": "ready",
    "database": "postgresql",
    "timestamp": "2026-10-30T20:42:00"
  }
  ```

---

## 2. Employee Directory & 360 Profiles

### `GET /api/v1/employees/`
- **Summary:** Paginated employee directory.
- **Query Parameters:**
  - `page` (int, default: 1)
  - `page_size` (int, default: 50, max: 200)
  - `department_id` (str, optional)
  - `role_id` (str, optional)
  - `status` (str, optional: `ACTIVE`, `TERMINATED`, `RETIRED`)
  - `risk_tier` (str, optional: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
  - `search` (str, optional: search by name or email)
  - `sort_by` (str, default: `employee_id`)
  - `sort_order` (str, default: `asc`)
- **Response:** `200 OK` (Array of employee cards with pagination envelope)

### `GET /api/v1/employees/{employee_id}`
- **Summary:** Core demographic, employment, and status record.
- **Response:** `200 OK` or `404 Not Found`

### `GET /api/v1/employees/{employee_id}/profile-360`
- **Summary:** Comprehensive 360-degree talent dossier synthesizing compensation, history, performance, engagement, project allocations, and flight risk score.
- **Responsible AI Isolation:** Ground-truth exit outcomes (`separation_type`, `exit_interview_completed`) are quarantined and never served in operational profiles.

---

## 3. Organizational Structure & Roles

### `GET /api/v1/departments/`
- **Summary:** Organizational departments with active headcount, cost center code, and division.

### `GET /api/v1/departments/{department_id}`
- **Summary:** Department detail including manager, roles, and aggregate retention metrics.

### `GET /api/v1/roles/`
- **Summary:** Job catalog roles, career tracks, and compensation midpoints. Filterable by `department_id`.

---

## 4. Operational & Restricted Retention Analytics

### `GET /api/v1/analytics/attrition/summary`
- **Summary:** Active workforce retention KPIs: total active headcount, active retention alerts, risk tier distributions, and top organizational flight drivers.
- **Response:** `200 OK`

### `GET /api/v1/analytics/attrition/trends`
- **Summary:** Historical separation trends by quarter, reason, and regret status.
- **Security Requirement:** Restricted ground-truth access. Requires header `X-HR-Authorization: true`. Requests lacking this header return `HTTP 403 Forbidden`.

### `GET /api/v1/analytics/engagement/trends`
- **Summary:** Longitudinal survey metrics over time: job satisfaction, work-life balance, management trust, burnout risk, and sentiment.

### `GET /api/v1/analytics/workload`
- **Summary:** Team allocation percentages and overtime risk metrics (`>45h/week`).

---

## 5. Prospective Retention Predictions & SHAP Explainability

### `GET /api/v1/predictions/model-metrics`
- **Summary:** Prospective Random Forest test metrics: ROC-AUC, PR-AUC, Brier score, ECE, operational decision threshold (0.05).

### `GET /api/v1/predictions/feature-importance`
- **Summary:** Global mean absolute SHAP values across all 13 point-in-time features.

### `GET /api/v1/predictions/calibration-report`
- **Summary:** Platt calibration reliability diagram curve and calibration error (ECE).

### `GET /api/v1/predictions/{employee_id}`
- **Summary:** Individual flight risk inference, risk tier classification, and localized top-5 SHAP feature contributions explaining the prediction.

---

## 6. Retention Interventions (Human-in-the-Loop Workflow)

### `GET /api/v1/interventions/`
- **Summary:** Filterable list of proposed, approved, active, and completed retention actions.

### `POST /api/v1/interventions/`
- **Summary:** Submit a human-governed retention intervention proposal (e.g. `COMPENSATION_ADJUSTMENT`, `ROLE_REDESIGN`, `EXECUTIVE_SPONSORSHIP`).

### `PATCH /api/v1/interventions/{intervention_id}/status`
- **Summary:** Advance or reject an intervention state transition (`PROPOSED` $\rightarrow$ `APPROVED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`). Requires reviewer identity and rationale. Automated state advances are rejected.

### `DELETE /api/v1/interventions/{intervention_id}`
- **Summary:** Mark an intervention as cancelled with an audit trail entry.

---

## 7. Data Quality & 12-Pillar Validation

### `GET /api/v1/validation/summary`
- **Summary:** Overall data quality scorecard across all 12 referential, temporal, and arithmetic integrity pillars.

### `GET /api/v1/validation/anomalies`
- **Summary:** Quarantined data anomalies with scenario classification and severity.

---

## 8. Audit Logging & Governance

### `GET /api/v1/audit/logs`
- **Summary:** Chronological compliance audit ledger tracking state mutations, user interventions, and security gate access.

### `GET /api/v1/audit/logs/entity/{entity_type}/{entity_id}`
- **Summary:** Full lifecycle audit history for a specific entity.

---

## 9. Data Exports & Reporting (Phase 8 Endpoints)

| Endpoint | Method | Format | Auth Requirement | Description |
|---|---|---|---|---|
| `/api/v1/exports/manifest` | `GET` | JSON | None | Catalog of all available exportable datasets and metadata |
| `/api/v1/exports/employees.csv` | `GET` | CSV | None | Filterable operational employee directory |
| `/api/v1/exports/employees.json` | `GET` | JSON | None | Employee directory wrapped in SHA-256 `ExportEnvelope` |
| `/api/v1/exports/departments.csv` | `GET` | CSV | None | Headcount and budget metrics by department |
| `/api/v1/exports/departments.json`| `GET` | JSON | None | Department analytics with SHA-256 verification |
| `/api/v1/exports/retention-risk.csv` | `GET` | CSV | None | Retention forecasts, risk tiers, and primary SHAP drivers |
| `/api/v1/exports/retention-risk.json`| `GET` | JSON | None | Risk predictions with embedded ethics disclaimers |
| `/api/v1/exports/interventions.csv` | `GET` | CSV | None | Human-governed retention action proposals and statuses |
| `/api/v1/exports/interventions.json`| `GET` | JSON | None | Retention action lifecycle records |
| `/api/v1/exports/engagement.csv` | `GET` | CSV | None | Longitudinal engagement metrics |
| `/api/v1/exports/engagement.json` | `GET` | JSON | None | Survey data with date and department filters |
| `/api/v1/exports/workload.csv` | `GET` | CSV | None | Project allocations and overtime fatigue indicators |
| `/api/v1/exports/workload.json` | `GET` | JSON | None | Overallocated workload export |
| `/api/v1/exports/validation.csv` | `GET` | CSV | None | 12-pillar audit scorecard in CSV format |
| `/api/v1/exports/validation.json` | `GET` | JSON | None | Complete 12-pillar audit results in JSON |
| `/api/v1/exports/model-metrics.csv`| `GET` | CSV | None | ROC-AUC, PR-AUC, Brier score, ECE metrics |
| `/api/v1/exports/model-metrics.json`| `GET`| JSON | None | Model performance benchmark artifact export |
| `/api/v1/exports/historical-separations.csv` | `GET` | CSV | `X-HR-Authorization: true` | Historical separation ground truth (**403 if omitted**) |
| `/api/v1/exports/historical-separations.json`| `GET` | JSON | `X-HR-Authorization: true` | Historical separation ground truth (**403 if omitted**) |
| `/api/v1/exports/reports/executive` | `GET` | JSON | None | Executive retention intelligence summary report |
