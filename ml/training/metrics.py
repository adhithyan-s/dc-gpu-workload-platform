"""
Shared evaluation metrics - every model in this project (naive baseline, and every real model after it) 
gets scored the same way, so results are directly comparable.
"""

from __future__ import annotations

from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, root_mean_squared_error


def evaluate_predictions(y_true, y_pred) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "mape_pct": float(mean_absolute_percentage_error(y_true, y_pred) * 100)
    }