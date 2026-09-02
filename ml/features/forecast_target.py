"""
Adds the forecasting target: the value of a column N buckets in the FUTURE relative to each row - 
what the model is trained to predict, given that row's features (which are all present-or-past information).
 
Uses shift(-horizon), the opposite direction from lag features (shift(+lag)): lag features pull the past forward into the present row; 
the target pulls the future backward into the present row. 
This means missing values land at the END of the table (no future data for the last rows), the mirror image of lag features leaving gaps at the START.
"""

from __future__ import annotations

import pandas as pd


def add_forecast_target(df: pd.DataFrame, column: str, horizon: int = 1) -> pd.DataFrame:
    """
    Adds a f"{column}_target" column containing `column`'s value `horizon` buckets ahead of each row. 
    horizon=1 means "predict 1 bucket (15 min) ahead". 
    The last `horizon` rows will have NaN targets and should be dropped before training.
    """
    df = df.copy()
    df[f"{column}_target"] = df[column].shift(-horizon)
    return df