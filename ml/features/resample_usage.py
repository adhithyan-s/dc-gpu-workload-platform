"""
Converts pod-level intervals (creation_time -> deletion_time, each with a resource amount) into a resource-usage-over-time curve, 
using a sweep line: every pod contributes a +resource event at its creation and a -resource event at its deletion; 
sorting all events by time and walking them with a running total gives the exact usage at every point in time,
in one pass, regardless of how many buckets we later sample it at.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_usage_step_function(fact_df: pd.DataFrame, resource_col: str) -> pd.DataFrame:
    starts = pd.DataFrame(
        {
            "time": fact_df["creation_time"].to_numpy(),
            "delta": fact_df[resource_col].to_numpy()
        }
    )
    ends = pd.DataFrame(
        {
            "time": fact_df["deletion_time"].to_numpy(),
            "delta": -fact_df[resource_col].to_numpy()
        }
    )
    events = pd.concat([starts, ends], ignore_index=True).sort_values("time", kind="stable")
    events["cumulative"] = events["delta"].cumsum()
    return events[["time", "cumulative"]].reset_index(drop=True)


def sample_usage_at_times(step_function: pd.DataFrame, sample_times: np.ndarray) -> np.ndarray:
    event_times = step_function["time"].to_numpy()
    cumulative = step_function["cumulative"].to_numpy()

    idx = np.searchsorted(event_times, sample_times, side="right") - 1
    # Before the first event, usage is 0 (nothing has started yet).
    result = np.where(
        idx >= 0,
        cumulative[np.clip(idx, 0, len(cumulative) - 1)],
        0
    )
    return result


def build_bucketed_series(
        fact_df: pd.DataFrame,
        resource_col: str,
        window_start: float,
        window_end: float,
        bucket_seconds: float
) -> pd.DataFrame:
    step_function = build_usage_step_function(fact_df, resource_col)
    bucket_starts = np.arange(window_start, window_end, bucket_seconds)
    usage = sample_usage_at_times(step_function, bucket_starts)
    return pd.DataFrame(
        {
            "bucket_start": bucket_starts,
            resource_col: usage
        }
    )