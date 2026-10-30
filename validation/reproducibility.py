"""
WorkforceIQ Reproducibility Validator (Phase 4).

Executes the generation pipeline twice under an identical seed in independent
temporary directories and confirms bit-for-bit identical output by comparing:
  - Record counts for every dataset table.
  - SHA-256 checksums for every exported file.
  - Sampled employee IDs and foreign keys.
  - Dataset-level statistical metrics (salary, attrition rate, sentiment).

Exports the full comparison result to data/manifests/reproducibility_report.json.
"""

import hashlib
import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = PROJECT_ROOT / "data" / "manifests"


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _collect_file_hashes(root: Path) -> Dict[str, str]:
    """
    Recursively collect SHA-256 hashes for all .csv files under *root*.
    Returns a mapping of ``relative/path.csv -> sha256_hex``.
    JSON files are intentionally excluded because the generator records a
    ``generated_at`` timestamp inside dataset_manifest.json which differs
    between runs by wall-clock milliseconds.  CSV content is stable.
    """
    hashes: Dict[str, str] = {}
    for p in sorted(root.rglob("*.csv")):
        rel = p.relative_to(root).as_posix()
        hashes[rel] = _sha256(p)
    return hashes


def _collect_row_counts(root: Path) -> Dict[str, int]:
    """
    Count rows in every .csv under *root*, returning a mapping of
    ``relative/path.csv -> row_count`` (header excluded).
    """
    counts: Dict[str, int] = {}
    for p in sorted(root.rglob("*.csv")):
        rel = p.relative_to(root).as_posix()
        with open(p, "r", encoding="utf-8") as fh:
            # subtract 1 for the header row
            counts[rel] = max(0, sum(1 for _ in fh) - 1)
    return counts


def _collect_ids(run_dir: Path) -> Dict[str, List[str]]:
    """
    Sample the first 20 IDs from key entity tables to verify exact match.
    """
    gen = run_dir / "generated"
    gt = run_dir / "ground_truth"
    id_map: Dict[str, List[str]] = {}
    targets = {
        "employees": (gen / "employees.csv", "employee_id"),
        "departments": (gen / "departments.csv", "department_id"),
        "job_roles": (gen / "job_roles.csv", "role_id"),
        "compensation_records": (gen / "compensation_records.csv", "compensation_id"),
        "exit_records": (gt / "exit_records.csv", "exit_id"),
    }
    for name, (path, col) in targets.items():
        if path.exists():
            df = pd.read_csv(path, usecols=[col])
            id_map[name] = df[col].head(20).tolist()
    return id_map


def _collect_statistics(run_dir: Path) -> Dict[str, Any]:
    """
    Compute dataset-level summary statistics for comparison:
      - mean & std of base_salary in compensation_records
      - voluntary attrition rate (exit_records voluntary / total employees)
      - mean sentiment score in engagement_surveys
    """
    gen = run_dir / "generated"
    gt = run_dir / "ground_truth"
    stats: Dict[str, Any] = {}

    # Salary stats
    comp_path = gen / "compensation_records.csv"
    if comp_path.exists():
        df = pd.read_csv(comp_path, usecols=["base_salary"])
        stats["salary_mean"] = round(float(df["base_salary"].mean()), 4)
        stats["salary_std"] = round(float(df["base_salary"].std()), 4)

    # Attrition rate
    emp_path = gen / "employees.csv"
    exit_path = gt / "exit_records.csv"
    if emp_path.exists() and exit_path.exists():
        n_emp = len(pd.read_csv(emp_path, usecols=["employee_id"]))
        df_ex = pd.read_csv(exit_path, usecols=["separation_type"])
        n_vol = int((df_ex["separation_type"] == "VOLUNTARY").sum())
        stats["voluntary_attrition_rate"] = round(n_vol / max(n_emp, 1), 6)

    # Sentiment mean
    survey_path = gen / "engagement_surveys.csv"
    if survey_path.exists():
        df = pd.read_csv(survey_path, usecols=["sentiment_score"])
        stats["sentiment_mean"] = round(float(df["sentiment_score"].mean()), 6)

    return stats


# ---------------------------------------------------------------------------
# Main Reproducibility Runner
# ---------------------------------------------------------------------------

def run_reproducibility_check(
    employee_count: int = 150,
    seed: int = 20261022,
    export_report: bool = True,
) -> Dict[str, Any]:
    """
    Runs the WorkforceIQ data generator twice (same seed, same count) into
    separate temporary directories and compares all outputs.

    Parameters
    ----------
    employee_count : int
        Number of employees to generate per run (default 150 for speed).
    seed : int
        Deterministic random seed (default 20261022).
    export_report : bool
        If True, writes the comparison report to data/manifests/reproducibility_report.json.

    Returns
    -------
    Dict with keys: reproducible (bool), run_1, run_2, comparison details.
    """
    # Import here to avoid circular dependency when this module is imported
    from data_generator.generator import run_pipeline  # noqa: PLC0415

    tmp_run1 = Path(tempfile.mkdtemp(prefix="wfiq_run1_"))
    tmp_run2 = Path(tempfile.mkdtemp(prefix="wfiq_run2_"))

    report: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "employee_count": employee_count,
        "run_1_dir": str(tmp_run1),
        "run_2_dir": str(tmp_run2),
    }

    try:
        # ------------------------------------------------------------------
        # Run 1
        # ------------------------------------------------------------------
        print(f"\n{'='*60}")
        print(f"  REPRODUCIBILITY RUN 1  (seed={seed}, n={employee_count})")
        print(f"  Output -> {tmp_run1}")
        print(f"{'='*60}")
        t0 = time.perf_counter()
        run_pipeline(
            employee_count=employee_count,
            seed=seed,
            output_dir=tmp_run1,
            export_json=False,          # CSV only for deterministic binary diff
            inject_negative_scenarios=True,
        )
        run1_elapsed = round(time.perf_counter() - t0, 2)

        # ------------------------------------------------------------------
        # Run 2
        # ------------------------------------------------------------------
        print(f"\n{'='*60}")
        print(f"  REPRODUCIBILITY RUN 2  (seed={seed}, n={employee_count})")
        print(f"  Output -> {tmp_run2}")
        print(f"{'='*60}")
        t0 = time.perf_counter()
        run_pipeline(
            employee_count=employee_count,
            seed=seed,
            output_dir=tmp_run2,
            export_json=False,
            inject_negative_scenarios=True,
        )
        run2_elapsed = round(time.perf_counter() - t0, 2)

        report["run_1_elapsed_s"] = run1_elapsed
        report["run_2_elapsed_s"] = run2_elapsed

        # ------------------------------------------------------------------
        # Collect artefacts
        # ------------------------------------------------------------------
        hashes1 = _collect_file_hashes(tmp_run1)
        hashes2 = _collect_file_hashes(tmp_run2)

        counts1 = _collect_row_counts(tmp_run1)
        counts2 = _collect_row_counts(tmp_run2)

        ids1 = _collect_ids(tmp_run1)
        ids2 = _collect_ids(tmp_run2)

        stats1 = _collect_statistics(tmp_run1)
        stats2 = _collect_statistics(tmp_run2)

        # ------------------------------------------------------------------
        # Compare: SHA-256 checksums
        # ------------------------------------------------------------------
        all_files = sorted(set(hashes1.keys()) | set(hashes2.keys()))
        checksum_comparison: List[Dict[str, Any]] = []
        checksum_matches = 0
        checksum_mismatches = 0

        for f in all_files:
            h1 = hashes1.get(f, "MISSING")
            h2 = hashes2.get(f, "MISSING")
            match = h1 == h2
            checksum_comparison.append({
                "file": f,
                "run_1_sha256": h1,
                "run_2_sha256": h2,
                "match": match,
            })
            if match:
                checksum_matches += 1
            else:
                checksum_mismatches += 1

        # ------------------------------------------------------------------
        # Compare: Record counts
        # ------------------------------------------------------------------
        all_tables = sorted(set(counts1.keys()) | set(counts2.keys()))
        count_comparison: List[Dict[str, Any]] = []
        count_matches = 0
        count_mismatches = 0

        for t in all_tables:
            c1 = counts1.get(t, -1)
            c2 = counts2.get(t, -1)
            match = c1 == c2
            count_comparison.append({
                "file": t,
                "run_1_rows": c1,
                "run_2_rows": c2,
                "match": match,
            })
            if match:
                count_matches += 1
            else:
                count_mismatches += 1

        # ------------------------------------------------------------------
        # Compare: IDs
        # ------------------------------------------------------------------
        id_comparison: Dict[str, Any] = {}
        id_all_match = True
        for entity in ids1:
            match = ids1[entity] == ids2.get(entity, [])
            id_comparison[entity] = {
                "run_1_sample": ids1[entity][:5],
                "run_2_sample": ids2.get(entity, [])[:5],
                "match": match,
            }
            if not match:
                id_all_match = False

        # ------------------------------------------------------------------
        # Compare: Statistics
        # ------------------------------------------------------------------
        stat_comparison: Dict[str, Any] = {}
        stats_all_match = True
        for key in stats1:
            v1 = stats1[key]
            v2 = stats2.get(key)
            match = (v1 == v2)
            stat_comparison[key] = {
                "run_1": v1,
                "run_2": v2,
                "match": match,
            }
            if not match:
                stats_all_match = False

        # ------------------------------------------------------------------
        # Overall verdict
        # ------------------------------------------------------------------
        fully_reproducible = (
            checksum_mismatches == 0
            and count_mismatches == 0
            and id_all_match
            and stats_all_match
        )

        report.update({
            "reproducible": fully_reproducible,
            "checksum_comparison": {
                "files_compared": len(checksum_comparison),
                "matches": checksum_matches,
                "mismatches": checksum_mismatches,
                "details": checksum_comparison,
            },
            "record_count_comparison": {
                "tables_compared": len(count_comparison),
                "matches": count_matches,
                "mismatches": count_mismatches,
                "details": count_comparison,
            },
            "id_comparison": id_comparison,
            "statistics_comparison": {
                "all_match": stats_all_match,
                "details": stat_comparison,
            },
        })

    finally:
        # Always clean up temporary directories
        shutil.rmtree(tmp_run1, ignore_errors=True)
        shutil.rmtree(tmp_run2, ignore_errors=True)

    # ------------------------------------------------------------------
    # Export report
    # ------------------------------------------------------------------
    if export_report:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = MANIFESTS_DIR / "reproducibility_report.json"
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\n  Reproducibility report written -> {report_path}")

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_reproducibility_check(employee_count=150, seed=20261022)

    print(f"\n{'='*60}")
    status = "PASS: REPRODUCIBLE" if result["reproducible"] else "FAIL: NOT REPRODUCIBLE"
    print(f"  Status: {status}")
    print(f"  Checksum matches:    {result['checksum_comparison']['matches']} / "
          f"{result['checksum_comparison']['files_compared']}")
    print(f"  Checksum mismatches: {result['checksum_comparison']['mismatches']}")
    print(f"  Row-count matches:   {result['record_count_comparison']['matches']} / "
          f"{result['record_count_comparison']['tables_compared']}")
    print(f"  Row-count mismatches:{result['record_count_comparison']['mismatches']}")
    print(f"  ID samples match:    {all(v['match'] for v in result['id_comparison'].values())}")
    print(f"  Statistics match:    {result['statistics_comparison']['all_match']}")
    print(f"{'='*60}")
