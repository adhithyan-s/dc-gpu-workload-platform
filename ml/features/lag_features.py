"""
Adds lagged versions of a column to a time series DataFrame - "what was the value N buckets ago" - 
so a forecasting model has recent history as input, not just the current moment.
 
Lags are chosen based on the actual autocorrelation curve measured on gpu_milli (see docs/feature_engineering_notes.md), 
not arbitrarily: lag_1 (15 min), lag_4 (1hr), lag_8 (2hr), lag_16 (4hr), lag_96 (24hr).
"""

from __future__ import annotations

import pandas as pd


def add_lag_features(df: pd.DataFrame, column: str, lags: list[int]) -> pd.DataFrame:
    """
    Adds one new column per lag: f"{column}_lag_{lag}", containing the value of 'column' that many rows earlier. 
    Requires df to already be sorted in time order (build_bucketed_series/build_multi_resource_table already guarantee this).
 
    The first max(lags) rows will have NaN in the largest lag columns, since there's no earlier data to look back to - 
    these rows should be dropped before training (see build_feature_table.py).
    """
    df = df.copy()
    for lag in lags:
        df[f"{column}_lag_{lag}"] = df[column].shift(lag)
    return df