# WorkforceIQ – Machine Learning Feature Dictionary & Governance

**Platform:** WorkforceIQ – AI-Powered Workforce Retention Intelligence  
**Document Version:** 2.0.0 (Prospective Prediction Framework)  
**Audit Status:** PASSED (Zero Data Leakage Detected)  
**Target Label:** `voluntary_attrition_in_horizon` (Binary: 0 = Retained/Active, 1 = Voluntary Separation in Next 90 Days)

---

## 1. Prospective Prediction Methodology

Rather than static retrospective analysis, WorkforceIQ implements a prospective, point-in-time forecasting framework:

- **Prediction Date ($T_{\text{pred}}$)**: Quarterly evaluation points:
  $$\{2024\text{-}12\text{-}15, 2025\text{-}03\text{-}15, 2025\text{-}06\text{-}15, 2025\text{-}09\text{-}15, 2025\text{-}12\text{-}15, 2026\text{-}03\text{-}15, 2026\text{-}06\text{-}15, 2026\text{-}09\text{-}15\}$$
- **Eligible Employee Population**: Active employees with $\text{hire\_date} \le T_{\text{pred}}$ and no separation record prior to or on $T_{\text{pred}}$.
- **Prediction Horizon**: Strictly **90 days** $(T_{\text{pred}}, T_{\text{pred}} + 90\text{ days}]$.
- **Disjoint Outcome Windows**: Because consecutive quarterly prediction cycles are spaced 90 days apart, outcome observation windows are strictly non-overlapping.
- **Outcome Label Definition**:
  $$Y_{i, t} = \begin{cases} 1 & \text{if employee } i \text{ has an exit in } (T_{\text{pred}}, T_{\text{pred}} + 90\text{ days}] \text{ with separation\_type = 'VOLUNTARY'} \\ 0 & \text{otherwise} \end{cases}$$

---

## 2. Feature Timestamp Controls & Pre-Outcome Validity

All features are strictly evaluated using data available on or before $T_{\text{pred}}$:

| Feature Name | Type | Timestamp Constraint / Calculation Method | Source Entity |
| :--- | :--- | :--- | :--- |
| `tenure_months` | `float` | $(T_{\text{pred}} - \text{hire\_date}).\text{days} / 30.4375$. Exactly as-of $T_{\text{pred}}$. | `employees` |
| `base_salary` | `float` | Compensation active on $T_{\text{pred}}$: latest record with $\text{effective\_from} \le T_{\text{pred}}$. | `compensation_records` |
| `compa_ratio` | `float` | $base\_salary / role\_mid$ using the active role band midpoint on $T_{\text{pred}}$. | `compensation_records`, `job_roles` |
| `promotions_count` | `int` | Cumulative promotions with $\text{effective\_date} \le T_{\text{pred}}$. | `employee_history` |
| `avg_job_satisfaction` | `float` | Mean satisfaction across surveys with $\text{survey\_date} \le T_{\text{pred}}$. | `engagement_surveys` |
| `avg_work_life_balance`| `float` | Mean work-life balance across surveys with $\text{survey\_date} \le T_{\text{pred}}$. | `engagement_surveys` |
| `latest_burnout_risk` | `float` | Acute burnout index from the most recent survey on or before $T_{\text{pred}}$. | `engagement_surveys` |
| `latest_sentiment_score`| `float` | NLP sentiment score from the most recent survey on or before $T_{\text{pred}}$. | `engagement_surveys` |
| `avg_weekly_logged_hours`| `float` | Mean weekly hours in project assignments active during $[T_{\text{pred}} - 90\text{ days}, T_{\text{pred}}]$. | `project_assignments` |
| `grade_level` | `int` | Seniority grade level of active role on $T_{\text{pred}}$ ($[1, 15]$). | `job_roles` |
| `department_id` | `cat` | Organizational department assignment on $T_{\text{pred}}$. | `departments` |
| `work_location` | `cat` | Work arrangement on $T_{\text{pred}}$ (`REMOTE`, `HYBRID`, `ONSITE`). | `employees` |
| `employment_type` | `cat` | Contractual type on $T_{\text{pred}}$ (`FULL_TIME`, `PART_TIME`, `CONTRACT`). | `employees` |

---

## 3. Quarantined & Excluded Columns Register

| Column Name | Category | Reason for Quarantine / Exclusion |
| :--- | :--- | :--- |
| `has_attrited_voluntary` | Ground Truth | Target label. |
| `is_active` | Status Flag | In `employees.csv`, `is_active=False` is a 100% deterministic proxy for all separated staff. |
| `status` | Status Flag | `status='TERMINATED'` is a 100% deterministic proxy for departure. |
| `separation_date`, `exit_id` | Exit Ledger | Post-outcome termination records generated after separation. |
| `separation_type`, `regret_status` | Exit Ledger | Retrospective HR evaluations created after separation. |
| `exit_interview_notes` | Exit Ledger | Qualitative post-departure interview records. |
| `is_successful`, `outcome_evaluated_date` | Interventions | Post-intervention evaluation records. |
| `employee_id`, `name`, `email` | PII / Identifiers | Excluded to prevent memorization and ensure algorithmic fairness. |

---

## 4. Chronological Prediction-Date Splits

The dataset is partitioned chronologically by quarterly prediction periods:

```
[--- Training Periods: 2024-Q4 through 2025-Q4 ---]   [-- Validation: 2026-Q1 --]   [--- Test: 2026-Q2 ---]
Dates: 2024-12-15, 2025-03-15, 2025-06-15,            Date: 2026-03-15              Date: 2026-06-15
       2025-09-15, 2025-12-15                         Samples: 9,431                Samples: 9,729
Samples: 42,554 (549 voluntary exits - 1.29%)         Exits: 128 (1.36%)            Exits: 147 (1.51%)
```

- **Preprocessing Fit Isolation**: `ColumnTransformer` is strictly fitted on Training Set snapshots only.
- **Handling Repeated Employee Observations**: Employees appear once per active quarter. In cross-validation, `GroupKFold` or `TimeSeriesSplit` by `employee_id` ensures no intra-person snapshot leakage occurs across cross-validation folds.
- **Holdout Test Set**: Kept completely untouched during all model exploration and hyperparameter tuning.

---

## 5. Algorithmic Fairness & Department Proxy Audit

1. **Absence of Protected Demographics**:
   - `employees.csv` contains zero protected characteristics (gender, race, age, religion, disability, marital status).
2. **Evaluation of `department_id`**:
   - Baseline turnover rates across departments are evenly distributed:
     - Minimum: 7.32% (Customer Success)
     - Maximum: 11.02% (Enterprise Sales)
     - Average: 9.70%
     - Disparity Ratio: $1.50\times$ (within statistical parity limits).
   - Safeguard: SHAP feature attributions must reflect individual-level drivers (burnout, compa-ratio, hours) rather than macro department bias.
3. **Machine-Readable Audit**: Persisted at [`data/manifests/ml_feature_audit.json`](file:///c:/Users/sai/Desktop/WorkforceIQ/data/manifests/ml_feature_audit.json).
