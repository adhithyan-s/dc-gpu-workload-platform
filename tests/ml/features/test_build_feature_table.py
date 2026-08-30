import pandas as pd

from ml.features.build_feature_table import build_multi_resource_table


def _fact_df() -> pd.DataFrame:
    # pod-0: active [0, 100), cpu=10, mem=100, gpu=1
    # pod-1: active [50, 150), cpu=20, mem=200, gpu=2
    # overlap [50,100): 2 pods active, cpu=30, mem=300, gpu=3
    return pd.DataFrame(
        {
            "pod_id": ["pod-0", "pod-1"],
            "creation_time": [0, 50],
            "deletion_time": [100, 150],
            "cpu_milli": [10, 20],
            "memory_mib": [100, 200],
            "gpu_milli": [1, 2],
        }
    )


def test_all_expected_columns_present():
    table = build_multi_resource_table(_fact_df(), window_start=0, window_end=150, bucket_seconds=50)
    assert set(table.columns) == {
        "bucket_start", "cpu_milli", "memory_mib", "gpu_milli", "active_pod_count",
    }


def test_values_match_hand_calculated_overlap():
    table = build_multi_resource_table(_fact_df(), window_start=0, window_end=150, bucket_seconds=50)

    assert list(table["bucket_start"]) == [0, 50, 100]
    assert list(table["cpu_milli"]) == [10, 30, 20]
    assert list(table["memory_mib"]) == [100, 300, 200]
    assert list(table["gpu_milli"]) == [1, 3, 2]


def test_active_pod_count_correct():
    table = build_multi_resource_table(_fact_df(), window_start=0, window_end=150, bucket_seconds=50)
    # bucket 0: only pod-0 active -> 1; bucket 50: both -> 2; bucket 100: only pod-1 -> 1
    assert list(table["active_pod_count"]) == [1, 2, 1]


def test_no_nulls_in_output():
    table = build_multi_resource_table(_fact_df(), window_start=0, window_end=150, bucket_seconds=50)
    assert not table.isnull().any().any()