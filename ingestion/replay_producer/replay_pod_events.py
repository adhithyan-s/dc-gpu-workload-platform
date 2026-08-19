
"""
Replay producer: reads the openb_pod_list_default.csv and "replays" it in timestamp order, 
simulating pods arriving live, by writing timestamped micro-batches
to S3 at a controlled pace (or, by default, just printing what it would write - a dry run).
 
Usage:
    python -m ingestion.replay_producer.replay_pod_events --duration 6 --num-batches 30    # dry run
    python -m ingestion.replay_producer.replay_pod_events --duration 20 --num-batches 30 --upload     # real S3 writes
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd

from common.s3paths import Category, Zone, dataset_path


REPO_ROOT = Path(__file__).resolve().parents[2]
POD_LIST_PATH = REPO_ROOT / "data" / "raw" / "openb_pod_list_default.csv"

NUM_BATCHES = 30
REPLAY_DURATION_SECONDS = 60


def load_pod_events() -> pd.DataFrame:
    df = pd.read_csv(POD_LIST_PATH)
    return df.sort_values("creation_time").reset_index(drop=True)


def build_batches(df: pd.DataFrame, num_batches: int) -> list[pd.DataFrame]:
    '''Split events into batches of equal time_window using creation_time '''
    min_t, max_t = df.creation_time.min(), df.creation_time.max()
    edges = [
        min_t + (max_t - min_t) * i / num_batches for i in range(num_batches + 1)
        for i in range(num_batches + 1)
    ]

    batches = []
    for i in range(num_batches):
        lo, hi = edges[i], edges[i+1]
        if i == num_batches - 1:
            mask = (df.creation_time >= lo) & (df.creation_time <= hi)
        else:
            mask = (df.creation_time >= lo) & (df.creation_time < hi)
        batches.append(df[mask])

    return batches


def emit_batch(batch: pd.DataFrame, batch_index: int, bucket: str | None, upload: bool) -> None:
    if batch.empty:
        print(f"batch{batch_index:02d}: 0 events")
        return

    today = datetime.now(timezone.utc).date()
    s3_uri = dataset_path(
        bucket=bucket or "<bucket-not-set>",
        zone=Zone.RAW,
        category=Category.EVENTS,
        dataset="pod_list",
        dt=today,
        variant="default"
    )
    key_suffix = f"batch_{batch_index:03d}.csv"
    csv_bytes = batch.to_csv(index=False).encode("utf-8")

    if not upload:
        print(f"batch{batch_index:02d}: {len(batch)} events -> [DRY RUN] would write {s3_uri}{key_suffix}")
        return

    s3 = boto3.client("s3")
    key_prefix = s3_uri.split(f"s3://{bucket}/", 1)[1]
    full_key = f"{key_prefix}{key_suffix}"
    s3.put_object(Bucket=bucket, Key=full_key, Body=csv_bytes)
    print(f"batch{batch_index:02d}: {len(batch)} events -> uploaded s3://{bucket}/{full_key}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Actually write to s3 (default: DRY RUN)")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET_NAME"))
    parser.add_argument("--num-batches", type=int, default=NUM_BATCHES)
    parser.add_argument("--duration", type=int, default=REPLAY_DURATION_SECONDS)
    args = parser.parse_args()

    if args.upload and not args.bucket:
        raise SystemExit("--upload requires S3_BUCKET_NAME env var or --bucket")

    df = load_pod_events()
    batches = build_batches(df, args.num_batches)
    sleep_per_batch = args.duration / args.num_batches

    mode = "UPLOAD" if args.upload else "DRY RUN"
    print(f"Replaying {len(df)} pod events across {args.num_batches} batches over - {args.duration}s [{mode}]")

    for i, batch in enumerate(batches):
        emit_batch(batch, i, args.bucket, args.upload)
        time.sleep(sleep_per_batch)

    print("Replay complete.")


if __name__ == "__main__":
    main()