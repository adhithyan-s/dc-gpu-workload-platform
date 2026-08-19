"""
One-time upload of openb_node_list_all_node.csv to s3. 
Unlike pod_list, node_list isn't replayed over time - it's a slowly-changing dimension, uploaded whole in a single snapshot. 
The dt=partition here just marks "the date this snapshot was captured," in case we ever reload a newer topology snapshot later.
 
Usage:
    python -m ingestion.replay_producer.upload_node_list              # dry run
    python -m ingestion.replay_producer.upload_node_list --upload     # real S3 write
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3

from common.s3paths import Category, Zone, dataset_path


REPO_ROOT = Path(__file__).resolve().parents[2]
NODE_LIST_PATH = REPO_ROOT / "data" / "raw" / "openb_node_list_all_node.csv"


def resolve_source_path() -> Path:
    if not NODE_LIST_PATH.exists():
        raise FileNotFoundError(f"{NODE_LIST_PATH} not found - run the downloader first")
    return NODE_LIST_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Actually write to s3 (default: DRY RUN)")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET_NAME"))
    args = parser.parse_args()

    if args.upload and not args.bucket:
        raise SystemExit("--upload requires S3_BUCKET_NAME env var or --bucket")

    source_path = resolve_source_path()

    today = datetime.now(timezone.utc).date()
    s3_uri = dataset_path(
        bucket=args.bucket or "<bucket-not-set>",
        zone=Zone.RAW,
        category=Category.DIMENSIONS,
        dataset="node_list",
        dt=today,
        variant="all_nodes"
    )
    key_suffix = source_path.name

    if not args.upload:
        print(f"[DRY RUN] would upload {source_path} -> {s3_uri}{key_suffix}")
        return

    s3 = boto3.client("s3")
    key_prefix = s3_uri.split(f"s3://{args.bucket}/", 1)[1]
    full_key = f"{key_prefix}{key_suffix}"
    s3.upload_file(str(source_path), args.bucket, full_key)
    print(f"Uploaded {source_path} -> s3://{args.bucket}/{full_key}")


if __name__ == "__main__":
    main()