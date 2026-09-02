"""
Splits a time-ordered feature table into train/validation/test sets by chronological position, not randomly. 
Shuffling rows before splitting would let training see data from AFTER the point it's meant to predict - which the model will never have access to when actually deployed.
Splitting by position keeps validation and test strictly after training in time, honestly simulating "predicting data the model hasn't seen yet."
"""

from __future__ import annotations

import pandas as pd


def time_based_split(
    df: pd.DataFrame,
    train_frac: float = 0.7, 
    val_frac: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits a chronologically-sorted DataFrame into three chronological chunks: 
    the earliest train_frac of rows -> train, the next val_frac -> validation, everything remaining -> test. 
    Assumes df is already sorted in time order (true of every feature table this project builds).
    """
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train = df.iloc[:train_end].reset_index(drop=True)
    val = df.iloc[train_end:val_end].reset_index(drop=True)
    test = df.iloc[val_end:].reset_index(drop=True)
    return train, val, test
