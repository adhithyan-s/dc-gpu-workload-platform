
"""
Builds a single combined table of resource demand over time, at a fixed bucket size, 
across the trace's dense activity window - one column per resource, plus active pod count. 
This is the base table that lag/rolling features and the forecasting target get built on top of.
 
See docs/feature_engineering_notes.md for why 15-minute buckets and the dense window were chosen.
 
Usage:
    python -m ml.features.build_feature_table
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.features.lag_features import add_lag_features
from ml.features.resample_usage import build_bucketed_series
from ml.features.rolling_features import add_rolling_features

REPO_ROOT = Path(__file__).parents[2]
FACT_PATH = REPO_ROOT / "data" / "interim" / "fact_pod_events.parquet"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "feature_table_15min.parquet"

WINDOW_START = 9891350
WINDOW_END = 12901761
BUCKET_SECONDS = 900    # 15 minutes

RESOURCE_COLUMNS = ["cpu_milli", "memory_mib", "gpu_milli"]

# Chosen from gpu_milli's measured autocorrelation curve (see docs/feature_engineering_notes.md): 15min, 1hr, 2hr, 4hr, 24hr back.
GPU_MILLI_LAGS = [1, 4, 8, 16, 96]

# Matches the lag horizons for consistency: 1hr, 4hr, 24hr rolling windows.
GPU_MILLI_ROLLING_WINDOWS = [4, 16, 96]


def build_multi_resource_table(
        fact_df: pd.DataFrame,
        window_start: float,
        window_end: float,
        bucket_seconds: float
) -> pd.DataFrame:
    combined = None
    for col in RESOURCE_COLUMNS:
        series = build_bucketed_series(fact_df, col, window_start, window_end, bucket_seconds)
        combined = series if combined is None else combined.merge(series, on="bucket_start")

    # active pod count: reuse the same sweep-line machinery by giving every pod a constant "count" of 1 - the running total then IS the count of
    # currently-active pods, with no new logic needed.
    count_df = fact_df.copy()
    count_df["active_pod_count"] = 1
    count_series = build_bucketed_series(count_df, "active_pod_count", window_start, window_end, bucket_seconds)
    combined = combined.merge(count_series, on="bucket_start")

    return combined


def main() -> None:
    fact_df = pd.read_parquet(FACT_PATH)
    table = build_multi_resource_table(fact_df, WINDOW_START, WINDOW_END, BUCKET_SECONDS)

    table = add_lag_features(table, "gpu_milli", GPU_MILLI_LAGS)
    table = add_rolling_features(table, "gpu_milli", GPU_MILLI_ROLLING_WINDOWS)

    rows_before = len(table)
    table = table.dropna().reset_index(drop=True)
    rows_dropped = rows_before - len(table)
    max_history_needed = max(max(GPU_MILLI_LAGS), max(GPU_MILLI_ROLLING_WINDOWS))
    print(f"dropped {rows_dropped} rows with incomplete lag history (expected: {max_history_needed})\n\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUTPUT_PATH, index=False)
    print(f"{len(table)} rows, columns: {list(table.columns)}")
    print(f"-> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()