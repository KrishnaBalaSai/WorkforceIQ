# WorkforceIQ — Reproducibility Protocol

> **Phase 4 Document** | Version 1.0 | 2026-10-30

---

## 1. Overview

This document describes the deterministic seeding strategy, the reproducibility
verification protocol, and the benchmark results that confirm that the
WorkforceIQ synthetic data generator produces **bit-for-bit identical outputs**
across independent runs sharing the same seed.

---

## 2. Deterministic Seeding Design

### 2.1 The Challenge

Python's `random` module is seeded globally, making the generation of numeric
values reproducible. However, `uuid.uuid4()` draws entropy from `os.urandom()`,
which is **not** governed by the `random` seed — causing UUIDs to differ between
runs even when `random.seed()` is called.

### 2.2 The Solution: `generate_deterministic_uuid()`

All primary-key UUIDs are generated using a custom function defined in
[`data_generator/config.py`](../data_generator/config.py):

```python
import uuid
import random

def generate_deterministic_uuid() -> str:
    """Generates a UUID seeded by random state for 100% bit-for-bit reproducibility."""
    return str(uuid.UUID(int=random.getrandbits(128), version=4))
```

This draws 128 bits from the deterministic `random.getrandbits()` stream —
fully governed by the global seed — rather than from OS entropy. All entity
ID generators (`employee_id`, `compensation_id`, `survey_id`, etc.) call
this function exclusively.

### 2.3 Seed Value

| Parameter | Value |
|---|---|
| **Canonical seed** | `20261022` |
| **Seed call** | `random.seed(20261022)` at pipeline start |
| **Challenge requirement** | ✅ Matches YottaFlex.ai specification |

### 2.4 Seeding Point

The seed is set exactly once per pipeline invocation inside
`generate_core_demographics()` in
[`data_generator/demographics.py`](../data_generator/demographics.py):

```python
random.seed(seed)  # called as very first operation
```

This ensures that no upstream stochastic event can contaminate the seed state
before entity generation begins.

---

## 3. Reproducibility Verification Protocol

The full verification protocol is implemented in
[`validation/reproducibility.py`](../validation/reproducibility.py).

### 3.1 Protocol Steps

```
Step 1  →  Run pipeline(seed=20261022, n=150) into temp_dir_1/
Step 2  →  Run pipeline(seed=20261022, n=150) into temp_dir_2/
Step 3  →  Collect SHA-256 checksums for all CSVs in each run
Step 4  →  Collect row counts for all CSVs in each run
Step 5  →  Sample first-20 IDs from key entity tables in each run
Step 6  →  Compute dataset-level statistics from each run
Step 7  →  Compare: checksums, counts, IDs, statistics
Step 8  →  Declare reproducible if ALL comparisons pass
Step 9  →  Write data/manifests/reproducibility_report.json
Step 10 →  Delete temporary directories
```

### 3.2 Why CSVs Only (not JSON)

JSON export is disabled during reproducibility runs (`export_json=False`).
The `dataset_manifest.json` file embeds a `generated_at` wall-clock timestamp
that legitimately differs between runs. CSV content files contain no timestamps
and produce stable binary output.

### 3.3 Comparison Dimensions

| Dimension | Method | Failure Threshold |
|---|---|---|
| File checksums | SHA-256 hex digest equality | Any mismatch |
| Row counts | `sum(1 for _ in open(f)) - 1` | Any difference |
| Entity IDs | First 20 values from each key table | Any difference |
| Mean salary | `compensation_records.base_salary.mean()` rounded to 4 dp | Any difference |
| Std salary | `compensation_records.base_salary.std()` rounded to 4 dp | Any difference |
| Attrition rate | `voluntary_exits / total_employees` rounded to 6 dp | Any difference |
| Sentiment mean | `engagement_surveys.sentiment_score.mean()` rounded to 6 dp | Any difference |

---

## 4. Benchmark Verification Results

Executed: **2026-10-30** | Seed: `20261022` | Employee count: `150` (starter mode)

### 4.1 SHA-256 Checksum Table

> All 19/19 CSV files produced **identical** SHA-256 digests across both runs.

| File | SHA-256 (first 20 chars) | Match |
|---|---|---|
| `generated/attrition_risk_scores.csv` | `355722f8dd4d58ef2e47…` | ✅ |
| `generated/compensation_records.csv` | `3ac3c16319a3aacb00c6…` | ✅ |
| `generated/data_anomalies.csv` | `24d8a8dbc08e14aaad2a…` | ✅ |
| `generated/departments.csv` | `a89dacac6b24d5b1116b…` | ✅ |
| `generated/derived_workforce_features.csv` | `93b79dcecc9f3e1146cc…` | ✅ |
| `generated/employee_history.csv` | `8cf4bf67b672808a8bae…` | ✅ |
| `generated/employee_skills.csv` | `c90ea138f50d9ff951ae…` | ✅ |
| `generated/employees.csv` | `c9ec3162a5207b7b45c2…` | ✅ |
| `generated/engagement_surveys.csv` | `a2e8ee3b98e08d9c4786…` | ✅ |
| `generated/job_roles.csv` | `2523e891242d18cca32f…` | ✅ |
| `generated/performance_evaluations.csv` | `aa100467fdfc51ab0339…` | ✅ |
| `generated/project_assignments.csv` | `7ac57bcefcdf450d406c…` | ✅ |
| `generated/projects.csv` | `839e6cd471ac308d4912…` | ✅ |
| `generated/retention_interventions.csv` | `02673c3c2f4968f5e221…` | ✅ |
| `generated/skills.csv` | `9f3d2e7da3283a90168b…` | ✅ |
| `generated/time_off_records.csv` | `5bdaeb1aa5f3d04c931e…` | ✅ |
| `ground_truth/anomaly_manifest.csv` | `1cafc07df07707471636…` | ✅ |
| `ground_truth/attrition_labels.csv` | `056193ab54ccd464e57c…` | ✅ |
| `ground_truth/exit_records.csv` | `d0cab34130144b00798b…` | ✅ |

**Summary: 19 matches / 0 mismatches**

### 4.2 Record Count Table

| File | Run 1 Rows | Run 2 Rows | Match |
|---|---|---|---|
| `generated/attrition_risk_scores.csv` | 1,124 | 1,124 | ✅ |
| `generated/compensation_records.csv` | 167 | 167 | ✅ |
| `generated/data_anomalies.csv` | 8 | 8 | ✅ |
| `generated/departments.csv` | 8 | 8 | ✅ |
| `generated/derived_workforce_features.csv` | 150 | 150 | ✅ |
| `generated/employee_history.csv` | 167 | 167 | ✅ |
| `generated/employee_skills.csv` | 559 | 559 | ✅ |
| `generated/employees.csv` | 150 | 150 | ✅ |
| `generated/engagement_surveys.csv` | 1,039 | 1,039 | ✅ |
| `generated/job_roles.csv` | 120 | 120 | ✅ |
| `generated/performance_evaluations.csv` | 551 | 551 | ✅ |
| `generated/project_assignments.csv` | 906 | 906 | ✅ |
| `generated/projects.csv` | 36 | 36 | ✅ |
| `generated/retention_interventions.csv` | 21 | 21 | ✅ |
| `generated/skills.csv` | 12 | 12 | ✅ |
| `generated/time_off_records.csv` | 266 | 266 | ✅ |
| `ground_truth/anomaly_manifest.csv` | 8 | 8 | ✅ |
| `ground_truth/attrition_labels.csv` | 150 | 150 | ✅ |
| `ground_truth/exit_records.csv` | 17 | 17 | ✅ |

**Summary: 19 matches / 0 mismatches**

### 4.3 Dataset Statistics Comparison

| Metric | Run 1 | Run 2 | Match |
|---|---|---|---|
| Mean base salary | 197,264.3837 | 197,264.3837 | ✅ |
| Std dev base salary | 141,633.4089 | 141,633.4089 | ✅ |
| Voluntary attrition rate | 0.093333 | 0.093333 | ✅ |
| Mean sentiment score | 0.174601 | 0.174601 | ✅ |

### 4.4 Timing

| Run | Elapsed (seconds) |
|---|---|
| Run 1 | 0.17 s |
| Run 2 | 0.18 s |

> **Verdict: REPRODUCIBLE** — 100% identical outputs confirmed for seed 20261022.

---

## 5. Automated Tests

The reproducibility protocol is fully automated in
[`tests/test_reproducibility.py`](../tests/test_reproducibility.py), which
contains **24 tests** across 5 test classes:

| Class | Tests | Coverage |
|---|---|---|
| `TestReproducibilityOverall` | 5 | Runs complete, verdict, seed, count, report file |
| `TestChecksumComparison` | 6 | No mismatches, all files present, count, key files |
| `TestRecordCountComparison` | 4 | No mismatches, count, employees row count, positive |
| `TestIDComparison` | 4 | All IDs match, employee/compensation/exit IDs |
| `TestStatisticsComparison` | 5 | All stats, salary mean/std, attrition, sentiment |

```bash
# Run reproducibility tests
pytest tests/test_reproducibility.py -v

# Output:
# 24 passed in 1.69s
```

---

## 6. Reproducing the 10,000-Employee Production Dataset

```bash
# Generates into data/ using the canonical seed
python -m data_generator.generator --full --seed 20261022

# Or using the run_pipeline API:
from data_generator.generator import run_pipeline
run_pipeline(employee_count=10000, seed=20261022)
```

The production dataset was generated with these exact parameters and its
file checksums are recorded in
[`data/manifests/source_manifest.json`](../data/manifests/source_manifest.json).

---

## 7. Scope Limitations

| Limitation | Notes |
|---|---|
| Platform dependency | Checksums verified on Windows/Python 3.12.2. Float formatting may differ on Python 3.11 or earlier. |
| JSON timestamps | `dataset_manifest.json` embeds `generated_at` wall-clock time — intentionally excluded from checksum comparison. |
| Pandas version | Row order and float precision may differ across pandas major versions. Tested on pandas 2.x. |
