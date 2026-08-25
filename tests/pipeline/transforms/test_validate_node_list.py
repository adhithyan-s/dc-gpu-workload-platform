import pandas as pd

from pipeline.transforms.validate_node_list import (
    CHECKS,
    check_columns_present,
    check_model_matches_gpu_count,
    check_non_negative_gpu_count,
    check_positive_capacity,
    check_required_non_null,
    check_unique_node_ids,
    run_validation,
)


def _valid_df(**overrides) -> pd.DataFrame:
    """A minimal three-row DataFrame that passes every check. Tests override exactly one column to trigger exactly one failure."""
    base = {
        "sn": ["node-0", "node-1", "node-2"],
        "cpu_milli": [32000, 16000, 8000],
        "memory_mib": [262144, 131072, 65536],
        "gpu": [8, 0, 2],
        "model": ["A100", None, "V100M32"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_df_passes_every_check():
    df = _valid_df()
    results = run_validation(df)
    assert all(r.passed for r in results)


def test_check_columns_present_fails_when_missing():
    df = _valid_df().drop(columns=["model"])
    result = check_columns_present(df)
    assert not result.passed


def test_check_required_non_null_fails_on_null_sn():
    df = _valid_df(sn=["node-0", None, "node-2"])
    result = check_required_non_null(df)
    assert not result.passed


def test_check_unique_node_ids_fails_on_duplicate():
    df = _valid_df(sn=["node-0", "node-0", "node-2"])
    result = check_unique_node_ids(df)
    assert not result.passed


def test_check_positive_capacity_fails_on_zero_memory():
    df = _valid_df(memory_mib=[262144, 0, 65536])
    result = check_positive_capacity(df)
    assert not result.passed


def test_check_non_negative_gpu_count_fails_on_negative():
    df = _valid_df(gpu=[8, -1, 2])
    result = check_non_negative_gpu_count(df)
    assert not result.passed


def test_check_model_matches_gpu_count_fails_when_gpu_zero_but_model_set():
    df = _valid_df(gpu=[8, 0, 2], model=["A100", "T4", "V100M32"])  # node-1 has gpu=0 but a model
    result = check_model_matches_gpu_count(df)
    assert not result.passed


def test_check_model_matches_gpu_count_fails_when_gpu_positive_but_model_missing():
    df = _valid_df(gpu=[8, 0, 2], model=[None, None, "V100M32"])  # node-0 has gpu=8 but no model
    result = check_model_matches_gpu_count(df)
    assert not result.passed


def test_run_validation_returns_one_result_per_check():
    df = _valid_df()
    results = run_validation(df)
    assert len(results) == len(CHECKS)