"""
Builds the curated dimension tables from validated raw data:
- dim_qos (from pod_list.qos)
- dim_pod_phase (from pod_list.pod_phase)
- dim_node (from node_list - standalone; pod_list has no node reference)
 
Validates the raw data first (reusing the ERROR-level checks from validate_pod_list.py / validate_node_list.py) 
and refuses to build dimensions from data that fails validation.
 
Writes Parquet files to data/interim/ locally. 
With --upload, also pushes them to S3 under curated/dimensions/ (today's date partition).
 
Usage:
    python -m pipeline.transforms.build_dimensions      # local only
    python -m pipeline.transforms.build_dimensions --upload     # also push to S3
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd

from common.s3paths import Category, Zone, dataset_path
from pipeline.transforms.validate_node_list import NODE_LIST_PATH
from pipeline.transforms.validate_node_list import run_validation as validate_node_list
from pipeline.transforms.validate_pod_list import POD_LIST_PATH
from pipeline.transforms.validate_pod_list import run_validation as validate_pod_list
from pipeline.transforms.validate_pod_list import Severity


REPO_ROOT = Path(__file__).parents[2]
INTERIM_DIR = REPO_ROOT / "data" / "interim"


def _assert_no_errors(results, source_name: str) -> None:
    errors = [r for r in results if not r.passed and r.severity == Severity.ERROR]
    if errors:
        details = ";".join(f"{e.name}: {e.detail}" for e in errors)
        raise ValueError(f"{source_name} failed validation, refusing to build dimenstions: {details}")


def build_dim_qos(pod_df: pd.DataFrame) -> pd.DataFrame:
    unique_values = sorted(pod_df["qos"].dropna().unique())
    return pd.DataFrame(
        {
            "qos_id": range(1, len(unique_values)+1),
            "qos_name": unique_values
        }
    )

def build_dim_pod_phase(pod_df: pd.DataFrame) -> pd.DataFrame:
    unique_values = sorted(pod_df["pod_phase"].dropna().unique())
    return pd.DataFrame(
        {
            "pod_phase_id": range(1, len(unique_values)+1),
            "pod_phase_name": unique_values
        }
    )


def build_dim_node(node_df: pd.DataFrame) -> pd.DataFrame:
    dim = node_df.copy()
    dim.insert(0, "node_id", range(1, len(dim)+1))
    dim["has_gpu"] = dim["gpu"] > 0
    return dim.rename(columns={"sn": "node_serial"})


def upload_to_curated(local_path: Path, dataset_name: str, bucket: str) -> None:
    today = datetime.now(timezone.utc).date()
    s3_uri = dataset_path(bucket=bucket, zone=Zone.CURATED, category=Category.DIMENSIONS, dataset=dataset_name, dt=today)
    key_prefix = s3_uri.split(f"s3://{bucket}/", 1)[1]
    full_key = f"{key_prefix}{local_path.name}"

    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, full_key)
    print(f"Uploaded -> s3://{bucket}/{full_key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Also push results to s3 (default: local only)")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET_NAME"))
    args = parser.parse_args()

    if args.upload and not args.bucket:
        raise SystemExit("--upload requires S3_BUCKET_NAME env var or --bucket")

    pod_df = pd.read_csv(POD_LIST_PATH)
    node_df = pd.read_csv(NODE_LIST_PATH)

    print("Validating source data before building dimensions...")
    _assert_no_errors(validate_pod_list(pod_df), "pod_list")
    _assert_no_errors(validate_node_list(node_df), "node_list")
    print("OK\n")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    dimensions = {
        "dim_qos": build_dim_qos(pod_df),
        "dim_pod_phase": build_dim_pod_phase(pod_df),
        "dim_node": build_dim_node(node_df)
    }

    for name, dim_df in dimensions.items():
        local_path = INTERIM_DIR / f"{name}.parquet"
        dim_df.to_parquet(local_path, engine="pyarrow", index=False)
        print(f"{name}: {len(dim_df)} rows -> {local_path}")

        if args.upload:
            upload_to_curated(local_path, dim_df, args.bucket)

    print("\nDone.")


if __name__ == "__main__":
    main()