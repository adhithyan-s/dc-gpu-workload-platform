import math

import numpy as np

from ml.training.metrics import evaluate_predictions


def test_perfect_predictions_have_zero_error():
    y_true = np.array([10, 20, 30])
    y_pred = np.array([10, 20, 30])
    metrics = evaluate_predictions(y_true, y_pred)
    assert metrics["mae"] == 0
    assert metrics["rmse"] == 0
    assert metrics["mape_pct"] == 0


def test_mae_and_rmse_match_hand_calculation():
    y_true = np.array([10, 20, 30])
    y_pred = np.array([12, 18, 33])
    # errors: 2, -2, 3 -> abs errors: 2, 2, 3 -> MAE = 7/3
    metrics = evaluate_predictions(y_true, y_pred)
    assert abs(metrics["mae"] - (2 + 2 + 3) / 3) < 1e-6

    # RMSE = sqrt(mean(squared errors)) = sqrt((4+4+9)/3)
    expected_rmse = math.sqrt((4 + 4 + 9) / 3)
    assert abs(metrics["rmse"] - expected_rmse) < 1e-6


def test_mape_matches_hand_calculation():
    y_true = np.array([100, 200])
    y_pred = np.array([110, 180])
    # pct errors: |110-100|/100=10%, |180-200|/200=10% -> mean = 10%
    metrics = evaluate_predictions(y_true, y_pred)
    assert abs(metrics["mape_pct"] - 10.0) < 1e-6


def test_rmse_penalizes_large_errors_more_than_mae():
    # one big miss should hurt RMSE proportionally more than MAE
    y_true = np.array([100, 100, 100, 100])
    y_pred = np.array([100, 100, 100, 50])  # one big miss of 50
    metrics = evaluate_predictions(y_true, y_pred)
    assert metrics["rmse"] > metrics["mae"]