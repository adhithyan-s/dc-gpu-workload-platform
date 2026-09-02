import pandas as pd

from ml.features.forecast_target import add_forecast_target


def test_target_shifted_correctly_horizon_1():
    df = pd.DataFrame({"x": [10, 20, 30, 40, 50]})
    result = add_forecast_target(df, "x", horizon=1)

    # row0's target should be row1's x value (20), row1's target row2's x (30), etc.
    # last row has no future value -> NaN
    assert result["x_target"].isna().sum() == 1
    assert list(result["x_target"].dropna()) == [20, 30, 40, 50]


def test_target_shifted_correctly_horizon_4():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8]})
    result = add_forecast_target(df, "x", horizon=4)

    assert result["x_target"].isna().sum() == 4
    assert list(result["x_target"].dropna()) == [5, 6, 7, 8]


def test_missing_values_are_at_the_end_not_the_start():
    df = pd.DataFrame({"x": range(10)})
    result = add_forecast_target(df, "x", horizon=3)

    assert result["x_target"].iloc[:7].notna().all()  # first 7 rows all have a target
    assert result["x_target"].iloc[7:].isna().all()   # last 3 rows don't


def test_does_not_mutate_input_df():
    df = pd.DataFrame({"x": [1, 2, 3]})
    add_forecast_target(df, "x", horizon=1)
    assert "x_target" not in df.columns