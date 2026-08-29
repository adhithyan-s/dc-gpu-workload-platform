import numpy as np
import pandas as pd

from ml.features.resample_usage import (
    build_bucketed_series,
    build_usage_step_function,
    sample_usage_at_times,
)


def _simple_fact_df() -> pd.DataFrame:
    # pod-0: active [0, 100), using 10 units
    # pod-1: active [50, 150), using 20 units
    # so usage should be: 10 during [0,50), 30 during [50,100), 20 during [100,150), 0 after
    return pd.DataFrame(
        {
            "pod_id": ["pod-0", "pod-1"],
            "creation_time": [0, 50],
            "deletion_time": [100, 150],
            "cpu_milli": [10, 20],
        }
    )


def test_step_function_has_one_row_per_event():
    step = build_usage_step_function(_simple_fact_df(), "cpu_milli")
    assert len(step) == 4  # 2 pods x (start + end) each


def test_sample_usage_matches_hand_calculated_values():
    step = build_usage_step_function(_simple_fact_df(), "cpu_milli")

    sample_times = np.array([0, 25, 50, 75, 100, 125, 150, 200])
    usage = sample_usage_at_times(step, sample_times)

    expected = np.array([10, 10, 30, 30, 20, 20, 0, 0])
    np.testing.assert_array_equal(usage, expected)


def test_sample_usage_before_any_event_is_zero():
    step = build_usage_step_function(_simple_fact_df(), "cpu_milli")
    usage = sample_usage_at_times(step, np.array([-10]))
    assert usage[0] == 0


def test_build_bucketed_series_covers_expected_range():
    df = _simple_fact_df()
    series = build_bucketed_series(df, "cpu_milli", window_start=0, window_end=150, bucket_seconds=50)

    assert list(series["bucket_start"]) == [0, 50, 100]
    assert list(series["cpu_milli"]) == [10, 30, 20]


def test_total_usage_conserved_regardless_of_bucket_size():
    # Sanity check: fine and coarse sampling should agree at shared time points
    df = _simple_fact_df()
    step = build_usage_step_function(df, "cpu_milli")

    fine = sample_usage_at_times(step, np.array([75]))
    coarse = sample_usage_at_times(step, np.array([0, 75, 150]))
    assert fine[0] == coarse[1]