"""
Builds the curated fact table (fact_pod_events) by joining validated raw pod_list against the dim_qos / dim_pod_phase surrogate keys 
built by build_dimensions.py, plus a couple of derived columns.
 
Requires build_dimensions.py to have been run first (reads its output from data/interim/).
 
Usage:
    python -m pipeline.transforms.build_fact_pod_events     # local only
    python -m pipeline.transforms.build_fact_pod_events --upload     # also push to S3
"""


from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import boto3
import pandas as pd

from common.s3paths import Category, Zone, dataset_path
from pipeline.transforms.validate_pod_list import POD_LIST_PATH, Severity
from pipeline.transforms.validate_pod_list import run_validation as validate_pod_list

load_dotenv()

REPO_ROOT = Path(__file__).parents[2]
INTERIM_DIR = REPO_ROOT / "data" / "interim"

# gpu_spec is dropped: it's null for 100% of rows in this file variant (see docs/data_quality_notes.md), carrying no information. 
# Revisit if a different pod_list variant with real gpu_spec values is ever used.
DROPPED_COLUMNS = ["gpu_spec"]


def _assert_no_errors(results, source_name: str) -> None:
    errors = [r for r in results if not r.passed and r.severity == Severity.ERROR]
    if errors:
        details = "; ".join(f"{e.name}: {e.detail}" for e in errors)
        raise ValueError(f"{source_name} failed validation, refusing to build fact table: {details}")


def load_dimension(name: str) -> pd.DataFrame:
    path = INTERIM_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run build_dimensions.py first")
    return pd.read_parquet(path)


def build_fact_pod_events(
        pod_df: pd.DataFrame,
        dim_qos: pd.DataFrame, 
        dim_pod_phase: pd.DataFrame
) -> pd.DataFrame:
    original_row_count = len(pod_df)

    fact = pod_df.drop(columns=DROPPED_COLUMNS, errors="ignore").rename(columns={"name": "pod_id"})

    fact = fact.merge(dim_qos, left_on="qos", right_on="qos_name", how="left")
    fact = fact.merge(dim_pod_phase, left_on="pod_phase", right_on="pod_phase_name", how="left")
    fact = fact.drop(columns=["qos", "qos_name", "pod_phase", "pod_phase_name"])

    # Referential integrity check: every row must have matched a real key.
    # A null here means some pod's qos/pod_phase value isn't in the dimension table
    # e.g. dimensions were built from different source data. Silently keeping those rows would produce broken foreign keys.
    unmatched = fact["qos_id"].isnull() | fact["pod_phase_id"].isnull()
    if unmatched.any():
        raise ValueError(
            f"{unmatched.sum()} of {original_row_count} rows have a qos/pod_phase value "
            "not found in the dimension tables - rebuild dimensions from the same source data"
        )

    fact["duration_seconds"] = fact["deletion_time"] - fact["creation_time"]
    fact["wait_time_seconds"] = fact["scheduled_time"] - fact["creation_time"]
    fact["was_scheduled"] = fact["scheduled_time"].notnull()

    assert len(fact) == original_row_count, "row count changed during join - investigate before trusting this data"

    return fact


def upload_to_curated(local_path: Path, bucket: str) -> None:
    today = datetime.now(timezone.utc).date()
    s3_uri = dataset_path(bucket=bucket, zone=Zone.CURATED, category=Category.EVENTS, dataset="pod_events", dt=today)
    key_prefix = s3_uri.split(f"s3://{bucket}/", 1)[1]
    full_key = f"{key_prefix}{local_path.name}"

    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, full_key)
    print(f"uploaded -> s3://{bucket}/{full_key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Also push result to S3 (default: local only)")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET_NAME"))
    args = parser.parse_args()

    if args.upload and not args.bucket:
        raise SystemExit("--upload requires S3_BUCKET_NAME env var or --bucket")
 
    pod_df = pd.read_csv(POD_LIST_PATH)
 
    print("Validating source data before building fact table...")
    _assert_no_errors(validate_pod_list(pod_df), "pod_list")
    print("OK\n")

    dim_qos = load_dimension("dim_qos")
    dim_pod_phase = load_dimension("dim_pod_phase")
 
    fact = build_fact_pod_events(pod_df, dim_qos, dim_pod_phase)
 
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    local_path = INTERIM_DIR / "fact_pod_events.parquet"
    fact.to_parquet(local_path, index=False)
    print(f"fact_pod_events: {len(fact)} rows -> {local_path}")
 
    if args.upload:
        upload_to_curated(local_path, args.bucket)
 
    print("\nDone.")


if __name__ == "__main__":
    main()