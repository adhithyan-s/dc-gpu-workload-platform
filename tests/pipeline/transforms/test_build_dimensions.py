import pandas as pd
import pytest

from pipeline.transforms.build_dimensions import (
    _assert_no_errors,
    build_dim_node,
    build_dim_pod_phase,
    build_dim_qos,
)
from pipeline.transforms.validate_pod_list import run_validation as validate_pod_list


def _valid_pod_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["pod-0", "pod-1", "pod-2"],
            "cpu_milli": [1000, 2000, 500],
            "memory_mib": [1024, 2048, 512],
            "num_gpu": [1, 0, 0],
            "gpu_milli": [500, 0, 0],
            "gpu_spec": [None, None, None],
            "qos": ["LS", "BE", "LS"],
            "pod_phase": ["Running", "Pending", "Running"],
            "creation_time": [0, 100, 50],
            "deletion_time": [50, 200, 90],
            "scheduled_time": [10, None, 55],
        }
    )


def _valid_node_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sn": ["node-0", "node-1"],
            "cpu_milli": [32000, 16000],
            "memory_mib": [262144, 131072],
            "gpu": [8, 0],
            "model": ["A100", None],
        }
    )


def test_build_dim_qos_has_one_row_per_unique_value_no_duplicates():
    df = build_dim_qos(_valid_pod_df())
    assert sorted(df["qos_name"]) == ["BE", "LS"]  # LS appears twice in source, once here
    assert df["qos_id"].is_unique


def test_build_dim_pod_phase_has_one_row_per_unique_value():
    df = build_dim_pod_phase(_valid_pod_df())
    assert sorted(df["pod_phase_name"]) == ["Pending", "Running"]


def test_build_dim_node_adds_surrogate_key_and_has_gpu_flag():
    df = build_dim_node(_valid_node_df())
    assert list(df["node_id"]) == [1, 2]
    assert list(df["has_gpu"]) == [True, False]
    assert "node_serial" in df.columns  # renamed from sn


def test_assert_no_errors_raises_on_invalid_data():
    bad_df = _valid_pod_df()
    bad_df.loc[0, "name"] = None  # triggers required_columns_not_null ERROR

    results = validate_pod_list(bad_df)
    with pytest.raises(ValueError, match="failed validation"):
        _assert_no_errors(results, "pod_list")


def test_assert_no_errors_passes_on_valid_data():
    results = validate_pod_list(_valid_pod_df())
    _assert_no_errors(results, "pod_list")  # should not raise