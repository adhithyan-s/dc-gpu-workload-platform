import pandas as pd
import pytest

from pipeline.transforms.build_fact_pod_events import build_fact_pod_events


def _pod_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["pod-0", "pod-1", "pod-2"],
            "cpu_milli": [1000, 2000, 500],
            "memory_mib": [1024, 2048, 512],
            "num_gpu": [1, 0, 0],
            "gpu_milli": [500, 0, 0],
            "gpu_spec": [None, None, None],
            "qos": ["LS", "BE", "LS"],
            "pod_phase": ["Running", "Pending", "Succeeded"],
            "creation_time": [0, 100, 50],
            "deletion_time": [50, 200, 90],
            "scheduled_time": [10, None, 55],
        }
    )


def _dim_qos() -> pd.DataFrame:
    return pd.DataFrame({"qos_id": [1, 2], "qos_name": ["BE", "LS"]})


def _dim_pod_phase() -> pd.DataFrame:
    return pd.DataFrame(
        {"pod_phase_id": [1, 2, 3], "pod_phase_name": ["Pending", "Running", "Succeeded"]}
    )


def test_row_count_preserved():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert len(fact) == 3


def test_qos_and_pod_phase_replaced_with_foreign_keys():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert "qos" not in fact.columns
    assert "pod_phase" not in fact.columns
    assert "qos_id" in fact.columns
    assert "pod_phase_id" in fact.columns
    assert not fact["qos_id"].isnull().any()
    assert not fact["pod_phase_id"].isnull().any()


def test_pod_id_renamed_from_name():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert "pod_id" in fact.columns
    assert "name" not in fact.columns
    assert list(fact["pod_id"]) == ["pod-0", "pod-1", "pod-2"]


def test_duration_seconds_computed_correctly():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert list(fact["duration_seconds"]) == [50, 100, 40]


def test_was_scheduled_matches_scheduled_time_presence():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert list(fact["was_scheduled"]) == [True, False, True]


def test_gpu_spec_dropped():
    fact = build_fact_pod_events(_pod_df(), _dim_qos(), _dim_pod_phase())
    assert "gpu_spec" not in fact.columns


def test_raises_when_dimension_missing_a_value():
    # dim_qos is missing "LS" entirely - every LS row should fail to match
    incomplete_dim_qos = pd.DataFrame({"qos_id": [1], "qos_name": ["BE"]})

    with pytest.raises(ValueError, match="not found in the dimension tables"):
        build_fact_pod_events(_pod_df(), incomplete_dim_qos, _dim_pod_phase())