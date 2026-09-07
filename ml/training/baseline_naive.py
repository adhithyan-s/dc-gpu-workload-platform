"""
Naive "persistence" baseline: predicts that gpu_milli demand 15 minutes from now will be the same as demand right now (no change). 
This isn't meant to be a good model - it's the bar any real model must beat to be worth using. 
If a fancier model can't outperform "just guess the current value", it isn't adding real value.

Logs to MLflow (local ./mlruns/ folder, no server needed) so this baseline's numbers are recorded permanently 
and comparable against every future model, not just printed to a terminal that gets closed.
 
Usage:
    python -m ml.training.baseline_naive
"""

from __future__ import annotations

from pathlib import Path

import mlflow
import pandas as pd

from ml.features.time_split import time_based_split
from ml.training.metrics import evaluate_predictions

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURE_TABLE_PATH = REPO_ROOT / "data" / "processed" / "feature_table_15min.parquet"

EXPERIMENT_NAME = "gpu-demand-forecasting"


def main() -> None:
    mlflow.set_experiment(EXPERIMENT_NAME)

    df = pd.read_parquet(FEATURE_TABLE_PATH)
    train, val, test = time_based_split(df)

    with mlflow.start_run(run_name="naive_persistence_baseline"):
        mlflow.log_param("model_type", "naive_persistence")
        mlflow.log_param("forecast_horizon_buckets", 1)
        mlflow.log_param("bucket_minutes", 15)
        mlflow.log_param("train_rows", len(train))
        mlflow.log_param("val_rows", len(val))
        mlflow.log_param("test_rows", len(test))

        print("Naive baseline (predict: no change from current gpu_milli)\n")
        for name, split in [("train", train), ("val", val), ("test", test)]:
            y_true = split["gpu_milli_target"]
            y_pred = split["gpu_milli"]     # the naive "prediction" is just the current value
            metrics = evaluate_predictions(y_true, y_pred)
            print(f"{name:<5} MAE={metrics['mae']:>8.1f}  RMSE={metrics['rmse']:>8.1f}  MAPE={metrics['mape_pct']:>5.2f}%")

            for metric_name, value in metrics.items():
                mlflow.log_metric(f"{name}_{metric_name}", value)


if __name__ == "__main__":
    main()