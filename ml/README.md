# ml/

- `features/` - feature engineering (lag features, rolling stats) built on top of the curated data layer.
- `training/` - model training scripts, MLflow experiment tracking.
- `evaluation/` - offline evaluation, backtesting, error analysis.
- `models/` - local model artifact cache (gitignored; real artifacts live in the MLflow registry / S3).
