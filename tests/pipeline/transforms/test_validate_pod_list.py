import pandas as pd

from pipeline.transforms.validate_pod_list import (
    CHECKS,
    Severity,
    check_columns_present,
    check_deletion_after_creation,
    check_known_pod_phases,
    check_known_qos_values,
    check_non_negative_gpu_fields,
    check_positive_cpu,
    check_positive_memory,
    check_required_non_null,
    check_scheduled_time_nulls_match_pending,
    check_unique_pod_names,
    run_validation,
)


def _valid_df(**overrides) -> pd.DataFrame:
    """A minimal two-row DataFrame that passes every check. Tests override exactly one column to trigger exactly one failure."""
    base = {
        "name": ["pod-0", "pod-1"],
        "cpu_milli": [1000, 2000],
        "memory_mib": [1024, 2048],
        "num_gpu": [1, 0],
        "gpu_milli": [500, 0],
        "gpu_spec": [None, None],
        "qos": ["LS", "BE"],
        "pod_phase": ["Running", "Pending"],
        "creation_time": [0, 100],
        "deletion_time": [50, 200],
        "scheduled_time": [10, None],  # None is fine - pod-1 is Pending
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_df_passes_every_check():
    df = _valid_df()
    results = run_validation(df)
    assert all(r.passed for r in results)


def test_check_columns_present_fails_when_missing():
    df = _valid_df().drop(columns=["qos"])
    result = check_columns_present(df)
    assert not result.passed
    assert result.severity == Severity.ERROR


def test_check_required_non_null_fails_on_null_name():
    df = _valid_df(name=["pod-0", None])
    result = check_required_non_null(df)
    assert not result.passed


def test_check_scheduled_time_nulls_match_pending_fails_when_running_pod_has_null():
    df = _valid_df(pod_phase=["Running", "Running"], scheduled_time=[10, None])
    result = check_scheduled_time_nulls_match_pending(df)
    assert not result.passed


def test_check_scheduled_time_nulls_match_pending_passes_when_pending_has_null():
    df = _valid_df()  # pod-1 is Pending with null scheduled_time already
    result = check_scheduled_time_nulls_match_pending(df)
    assert result.passed


def test_check_unique_pod_names_fails_on_duplicate():
    df = _valid_df(name=["pod-0", "pod-0"])
    result = check_unique_pod_names(df)
    assert not result.passed


def test_check_deletion_after_creation_fails_when_deleted_before_created():
    df = _valid_df(creation_time=[100, 100], deletion_time=[50, 200])
    result = check_deletion_after_creation(df)
    assert not result.passed


def test_check_positive_cpu_fails_on_zero():
    df = _valid_df(cpu_milli=[0, 2000])
    result = check_positive_cpu(df)
    assert not result.passed
    assert result.severity == Severity.ERROR


def test_check_positive_memory_fails_on_zero_but_is_warning_not_error():
    df = _valid_df(memory_mib=[0, 2048])
    result = check_positive_memory(df)
    assert not result.passed
    assert result.severity == Severity.WARNING  # known anomaly - flagged, not blocking


def test_check_non_negative_gpu_fields_fails_on_negative_num_gpu():
    df = _valid_df(num_gpu=[-1, 0])
    result = check_non_negative_gpu_fields(df)
    assert not result.passed


def test_check_known_qos_values_fails_on_unrecognized_value():
    df = _valid_df(qos=["LS", "SuperPriority"])
    result = check_known_qos_values(df)
    assert not result.passed


def test_check_known_pod_phases_fails_on_unrecognized_value():
    df = _valid_df(pod_phase=["Running", "Zombified"])
    result = check_known_pod_phases(df)
    assert not result.passed


def test_run_validation_returns_one_result_per_check():
    df = _valid_df()
    results = run_validation(df)
    assert len(results) == len(CHECKS)