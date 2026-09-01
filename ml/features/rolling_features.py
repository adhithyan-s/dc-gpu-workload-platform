
"""
Adds rolling mean/std features to a time series - "what has demand looked like over the recent window," 
smoothing short-term noise and capturing trend/volatility, on top of the point-in-time lag features.
 
Windows match the lag features chosen from gpu_milli's autocorrelation curve (see docs/feature_engineering_notes.md): 1hr (4 buckets), 4hr (16 buckets), 24hr (96 buckets).
 
pandas' .rolling() is right-aligned by default: each row's rolling stat uses that row and the window-1 rows BEFORE it - never rows after it. 
This is essential for forecasting; a feature that could see the future would leak information the model wouldn't actually have at prediction time.
"""

from __future__ import annotations

import pandas as pd


def add_rolling_features(df: pd.DataFrame, column: str, windows: list[int]) -> pd.DataFrame:
    """
    Adds two columns per window: f"{column}_rolling_mean_{window}" and f"{column}_rolling_std_{window}". 
    The first window-1 rows will be NaN for each window, since there isn't yet enough history to compute it.
    """
    df = df.copy()
    for window in windows:
        df[f"{column}_rolling_mean_{window}"] = df[column].rolling(window=window).mean()
        df[f"{column}_rolling_std_{window}"] = df[column].rolling(window=window).std()

    return df
