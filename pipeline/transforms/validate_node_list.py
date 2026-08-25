"""
Validates data quality of the raw node_list dimension table (cluster topology snapshot) before it's trusted for curated modeling. Read-only -
never modifies data/raw/, only reports.
 
Checks are grounded in the real data (see docs/data_quality_notes.md):
model is null exactly when gpu == 0, with zero exceptions across all 1,523 rows - so that relationship is checked directly, not as a warning.
 
Usage:
    python -m pipeline.transforms.validate_node_list
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
NODE_LIST_PATH = REPO_ROOT / "data" / "raw" / "openb_node_list_all_node.csv"

EXPECTED_COLUMNS = ["sn", "cpu_milli", "memory_mib", "gpu", "model"]

# model is legitimately null when gpu == 0 - checked separately, 
# so it's excluded from the blanket non-null check.
REQUIRED_NON_NULL_COLUMNS = ["sn", "cpu_milli", "memory_mib", "gpu"]
 
 
class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
 
 
@dataclass
class CheckResult:
    name: str
    severity: Severity
    passed: bool
    detail: str
 
 
def check_columns_present(df: pd.DataFrame) -> CheckResult:
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    passed = not missing
    return CheckResult(
        "expected_columns_present", Severity.ERROR, passed,
        "all expected columns present" if passed else f"missing columns: {missing}",
    )
 
 
def check_required_non_null(df: pd.DataFrame) -> CheckResult:
    null_counts = {
        c: int(df[c].isnull().sum())
        for c in REQUIRED_NON_NULL_COLUMNS
        if c in df.columns and df[c].isnull().sum() > 0
    }
    passed = not null_counts
    return CheckResult(
        "required_columns_not_null", Severity.ERROR, passed,
        "no unexpected nulls" if passed else f"unexpected nulls found: {null_counts}",
    )
 
 
def check_unique_node_ids(df: pd.DataFrame) -> CheckResult:
    dupes = int(df["sn"].duplicated().sum())
    passed = dupes == 0
    return CheckResult(
        "unique_node_ids", Severity.ERROR, passed,
        "all node ids (sn) unique" if passed else f"{dupes} duplicate node ids found",
    )
 
 
def check_positive_capacity(df: pd.DataFrame) -> CheckResult:
    bad = int(((df["cpu_milli"] <= 0) | (df["memory_mib"] <= 0)).sum())
    passed = bad == 0
    return CheckResult(
        "positive_capacity", Severity.ERROR, passed,
        "all cpu_milli/memory_mib > 0" if passed else f"{bad} rows with non-positive capacity",
    )
 
 
def check_non_negative_gpu_count(df: pd.DataFrame) -> CheckResult:
    bad = int((df["gpu"] < 0).sum())
    passed = bad == 0
    return CheckResult(
        "non_negative_gpu_count", Severity.ERROR, passed,
        "all gpu counts >= 0" if passed else f"{bad} rows with negative gpu count",
    )
 
 
def check_model_matches_gpu_count(df: pd.DataFrame) -> CheckResult:
    """model should be null iff gpu == 0 - verified true for all 1,523 real rows."""
    inconsistent = int(
        (((df["gpu"] == 0) & df["model"].notnull()) | ((df["gpu"] > 0) & df["model"].isnull())).sum()
    )
    passed = inconsistent == 0
    return CheckResult(
        "model_matches_gpu_count", Severity.ERROR, passed,
        "model is null iff gpu == 0, with no exceptions" if passed else f"{inconsistent} rows where gpu count and model disagree",
    )
 
 
CHECKS = [
    check_columns_present,
    check_required_non_null,
    check_unique_node_ids,
    check_positive_capacity,
    check_non_negative_gpu_count,
    check_model_matches_gpu_count,
]
 
 
def run_validation(df: pd.DataFrame) -> list[CheckResult]:
    return [check(df) for check in CHECKS]
 
 
def main() -> None:
    df = pd.read_csv(NODE_LIST_PATH)
    print(f"Validating {NODE_LIST_PATH} ({len(df)} rows)\n")
 
    results = run_validation(df)
    has_error = False
    for r in results:
        status = "PASS" if r.passed else f"FAIL [{r.severity.value}]"
        print(f"  [{status}] {r.name}: {r.detail}")
        if not r.passed and r.severity == Severity.ERROR:
            has_error = True
 
    print()
    if has_error:
        print("Validation FAILED - one or more ERROR-level checks did not pass.")
        raise SystemExit(1)
    print("Validation passed.")
 
 
if __name__ == "__main__":
    main()