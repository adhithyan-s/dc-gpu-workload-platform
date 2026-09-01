import pandas as pd

from ml.features.rolling_features import add_rolling_features


def test_rolling_mean_matches_hand_calculation():
    df = pd.DataFrame({"x": [10, 20, 30, 40, 50]})
    result = add_rolling_features(df, "x", windows=[2])

    # window=2: row0 has only 1 value available -> NaN
    # row1=(10+20)/2=15, row2=(20+30)/2=25, row3=(30+40)/2=35, row4=(40+50)/2=45
    assert result["x_rolling_mean_2"].isna().sum() == 1
    assert list(result["x_rolling_mean_2"].dropna()) == [15.0, 25.0, 35.0, 45.0]


def test_rolling_std_matches_pandas_reference():
    df = pd.DataFrame({"x": [10, 20, 30, 40, 50]})
    result = add_rolling_features(df, "x", windows=[2])
    expected = df["x"].rolling(window=2).std().dropna().tolist()
    assert list(result["x_rolling_std_2"].dropna()) == expected


def test_rolling_is_backward_looking_only_no_future_leakage():
    # Change ONLY the last value between two versions of the data.
    # If rolling features are correctly backward-only, every row except
    # the very last one must be completely unaffected by that change.
    df1 = pd.DataFrame({"x": [10, 20, 30, 40, 50]})
    df2 = pd.DataFrame({"x": [10, 20, 30, 40, 9999]})  # only the last value differs

    r1 = add_rolling_features(df1, "x", windows=[2])
    r2 = add_rolling_features(df2, "x", windows=[2])

    # .equals() (not ==) because NaN != NaN under normal comparison —
    # .equals() correctly treats matching NaNs as equal.
    assert r1["x_rolling_mean_2"][:-1].equals(r2["x_rolling_mean_2"][:-1])
    assert r1["x_rolling_std_2"][:-1].equals(r2["x_rolling_std_2"][:-1])


def test_creates_expected_columns():
    df = pd.DataFrame({"x": range(20)})
    result = add_rolling_features(df, "x", windows=[4, 16])
    assert "x_rolling_mean_4" in result.columns
    assert "x_rolling_std_4" in result.columns
    assert "x_rolling_mean_16" in result.columns
    assert "x_rolling_std_16" in result.columns


def test_does_not_mutate_input_df():
    df = pd.DataFrame({"x": [1, 2, 3]})
    add_rolling_features(df, "x", windows=[2])
    assert "x_rolling_mean_2" not in df.columns