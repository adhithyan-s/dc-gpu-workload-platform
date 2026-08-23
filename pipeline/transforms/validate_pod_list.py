"""
Validates data quality of the raw pod_list events table before it's trusted for curated/gold modeling. 
Read-only - never modifies data/raw/, only reports.
 
Checks are grounded in what we actually found exploring the real data (see docs/data_quality_notes.md), not assumptions:
- gpu_spec is null for every row in this file variant - expected, not an error.
- scheduled_time is null only for Pending pods - expected; null anywhere else would be a real problem.
- one known anomaly (pod with memory_mib == 0) is treated as a WARNING, not an ERROR - see docs/data_quality_notes.md for the reasoning.
 
Usage:
    python -m pipeline.transforms.validate_pod_list
"""


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
POD_LIST_PATH = REPO_ROOT / "data" / "raw" / "openb_pod_list_default.csv"

EXPECTED_COLUMNS = [
    "name", "cpu_milli", "memory_mib", "num_gpu", "gpu_milli",
    "gpu_spec", "qos", "pod_phase", "creation_time", "deletion_time", "scheduled_time",
]

KNOWN_QOS_VALUES = {"LS", "BE", "Burstable", "Guaranteed"}
KNOWN_POD_VALUES = {"Running", "Failed", "Pending", "Succeeded"}

# Required (must never be null), 
# deliberately excluded gpu_spec (always null here)
# and scheduled time (conditionally null, checked separately in check_scheduled_time_nulls)
REQUIRED_NON_NULL_COLUMNS = [
    "name", "cpu_milli", "memory_mib", "num_gpu", "gpu_milli",
    "qos", "pod_phase", "creation_time", "deletion_time",
]


class Severity(str, Enum):
    ERROR = "ERROR"     # blocks downstread use
    WARNING = "WARNING"     # worth knowing, but doesn't block


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
        "all expected columns present" if passed else f"missing columns: {missing}"
    )


def check_required_non_null(df: pd.DataFrame) -> CheckResult:
    null_counts = {
        c: int(df[c].isnull().sum())
        for c in REQUIRED_NON_NULL_COLUMNS
        if c in df.columns and df[c].isnull().sum() > 0
    }
    passed = not null_counts
    return CheckResult(
        check_required_non_null, Severity.ERROR, passed,
        "no unexpected nulls" if passed else f"unexpected nulls found: {null_counts}"
    )


def check_scheduled_time_nulls_match_pending(df: pd.DataFrame) -> CheckResult:
    """scheduled time should be null if and only if pod_phase == 'Pending'"""
    null_but_not_pending = int(((df.scheduled_time.isnull()) & (df.pod_phase != "Pending")).sum())
    passed = null_but_not_pending == 0
    return CheckResult(
        "check_scheduled_time_nulls_match_pending", Severity.ERROR, passed,
        "all scheduled_time nulls are Pending pods" if passed
        else f"{null_but_not_pending} rows have null scheduled_time but aren't Pending"
    )


def check_unique_pod_names(df: pd.DataFrame) -> CheckResult:
    dupes = int(df["name"].duplicated().sum())
    passed = dupes == 0
    return CheckResult(
        "check_unique_pod_names", Severity.ERROR, passed,
        "all pod names unique" if passed else f"{dupes} duplicated pod names found"
    )


def check_deletion_after_creation(df: pd.DataFrame) -> CheckResult:
    bad = int((df["deletion_time"] < df["creation_time"]).sum())
    passed = bad == 0
    return CheckResult(
        "check_deletion_after_creation", Severity.ERROR, passed,
        "all deletion_time >= creation_time" if passed else f"{bad} rows deleted before created"
    )


def check_positive_cpu(df: pd.DataFrame) -> CheckResult:
    bad = int((df["cpu_milli"] <= 0).sum())
    passed = bad == 0
    return CheckResult(
        "check_positive_cpu", Severity.ERROR, passed,
        "all cpu_milli > 0" if passed else f"{bad} rows with non-positive cpu_milli"
    )


def check_positive_memory(df: pd.DataFrame) -> CheckResult:
    # Known anomaly: one Succedded pod has memory_lib == 0. 
    # Treated as warning not a blocker - see docs/data_quality_notes.md
    bad = int((df["memory_mib"] <= 0).sum())
    passed = bad == 0
    return CheckResult(
        "check_positive_memory", Severity.WARNING, passed,
        "all memory_mib > 0" if passed else f"{bad} rows with non-positive memory_mib (see docs/data_qualtiy_notes.md)"
    )


def check_non_negative_gpu_fields(df: pd.DataFrame) -> CheckResult:
    bad = int(((df["num_gpu"] < 0) | (df["gpu_milli"] < 0)).sum())
    passed = bad == 0
    return CheckResult(
        "check_non_negative_gpu_fields", Severity.ERROR, passed,
        "all num_gpu/gpu_milli >= 0" if passed else f"{bad} rows with negative gpu fields"
    )


def check_known_qos_values(df: pd.DataFrame) -> CheckResult:
    unknown = sorted(set(df["qos"].dropna().unique()) - KNOWN_QOS_VALUES)
    passed = not unknown
    return CheckResult(
        "check_known_qos_values", Severity.ERROR, passed,
        "all qos values recognized" if passed else f"unrecognized qos values: {unknown}"
    )


def check_known_pod_phases(df: pd.DataFrame) -> CheckResult:
    unknown = sorted(set(df["pod_phase"].dropna().unique()) - KNOWN_POD_VALUES)
    passed = not unknown
    return CheckResult(
        "check_known_pod_phases", Severity.ERROR, passed,
        "all pod_phase values recognized" if passed else f"unrecognized pod_phase values: {unknown}"
    )


CHECKS = [
    check_columns_present,
    check_required_non_null,
    check_scheduled_time_nulls_match_pending,
    check_unique_pod_names,
    check_deletion_after_creation,
    check_positive_cpu,
    check_positive_memory,
    check_non_negative_gpu_fields,
    check_known_qos_values,
    check_known_pod_phases
]


def run_validation(df: pd.DataFrame) -> list[CheckResult]:
    return [check(df) for check in CHECKS]


def main() -> None:
    df = pd.read_csv(POD_LIST_PATH)
    print(f"Validating {POD_LIST_PATH} ({len(df)} rows\n)")

    results = run_validation(df)
    has_error = False
    for r in results:
        status = "PASS" if r.passed else f"FAIL [{r.severity.value}]"
        print(f"[{status}] {r.name}: {r.detail}")
        if not r.passed and r.severity == Severity.ERROR:
            has_error = True

    print()
    if has_error:
        print("Validation FAILED - one or more ERROR-level checks did not pass")
        raise SystemExit(1)
    print("Validation PASSED (warning, if any, are non-blocking)")


if __name__ == "__main__":
    main()