import pandas as pd

from ml.features.lag_features import add_lag_features


def test_lag_values_shifted_correctly():
    df = pd.DataFrame({"x": [10, 20, 30, 40, 50]})
    result = add_lag_features(df, "x", lags=[1, 2])

    assert result["x_lag_1"].isna().sum() == 1
    assert list(result["x_lag_1"].dropna()) == [10, 20, 30, 40]

    assert result["x_lag_2"].isna().sum() == 2
    assert list(result["x_lag_2"].dropna()) == [10, 20, 30]


def test_original_column_untouched():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = add_lag_features(df, "x", lags=[1])
    assert list(result["x"]) == [1, 2, 3]


def test_creates_one_column_per_lag():
    df = pd.DataFrame({"x": range(10)})
    result = add_lag_features(df, "x", lags=[1, 4, 8])
    assert "x_lag_1" in result.columns
    assert "x_lag_4" in result.columns
    assert "x_lag_8" in result.columns


def test_does_not_mutate_input_df():
    df = pd.DataFrame({"x": [1, 2, 3]})
    add_lag_features(df, "x", lags=[1])
    assert "x_lag_1" not in df.columns  # original df unaffected