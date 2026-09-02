import pandas as pd

from ml.features.time_split import time_based_split


def _time_ordered_df(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame({"bucket_start": range(n), "value": range(n)})


def test_split_sizes_match_fractions():
    df = _time_ordered_df(100)
    train, val, test = time_based_split(df, train_frac=0.7, val_frac=0.15)
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15


def test_all_rows_accounted_for_no_overlap():
    df = _time_ordered_df(100)
    train, val, test = time_based_split(df, train_frac=0.7, val_frac=0.15)
    assert len(train) + len(val) + len(test) == len(df)

    all_values = list(train["value"]) + list(val["value"]) + list(test["value"])
    assert sorted(all_values) == list(range(100))  # every original row appears exactly once


def test_chronological_order_preserved():
    df = _time_ordered_df(100)
    train, val, test = time_based_split(df, train_frac=0.7, val_frac=0.15)

    assert train["bucket_start"].max() < val["bucket_start"].min()
    assert val["bucket_start"].max() < test["bucket_start"].min()


def test_default_fractions():
    df = _time_ordered_df(200)
    train, val, test = time_based_split(df)
    assert len(train) == 140    # 0.7
    assert len(val) == 30   # 0.15
    assert len(test) == 30  # remainder