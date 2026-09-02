# Data Center GPU Workload Forecasting Platform

An end-to-end data engineering + ML engineering platform that ingests real data center GPU cluster telemetry, forecasts short-horizon resource demand (and predicts job failure risk), and serves the results through a live dashboard.

Built as a portfolio project targeting Data Engineer / ML Engineer roles, using the [Alibaba cluster-trace-gpu-v2023](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2023) dataset (~6,200 GPUs across ~1,200 machines, real production AI/ML workload traces).

## Why this project

Data centers are the physical substrate behind every cloud/AI product, and the teams that run them lean heavily on the same skill set this repo exercises: multi-source ingestion, a proper data lake, orchestrated transforms, a tracked ML training pipeline, and a served, monitored model behind a real dashboard - all built and deployed at (near) zero cost on the AWS free tier.

## Architecture

```
Alibaba GPU trace (static files)
        |
        v
[ingestion/downloader]      -- one-time fetch of source files
        |
        v
[ingestion/replay_producer] -- replays trace in timestamp order,
        |                       writing timestamped micro-batches
        |                       straight to S3, simulating a live feed
        v
   S3 data lake (raw -> interim -> processed)
        |
        v
[pipeline/transforms + dags] -- Airflow-orchestrated cleaning & feature build
        |
        v
[ml/training]  -- XGBoost/LightGBM forecasting + failure classification,
        |          tracked in MLflow
        v
[serving/api + lambda] -- containerized inference behind API Gateway
        |
        v
[dashboard] -- Streamlit/React front end for business-facing views
```

Full architecture notes: see `docs/architecture.md`.

## Repo layout

| Path | Purpose |
|---|---|
| `ingestion/` | Source downloader + the trace "replay producer" that simulates continuous ingestion |
| `pipeline/` | Data transforms and orchestration (Airflow DAGs) |
| `ml/` | Feature engineering, model training, evaluation |
| `serving/` | Inference API (FastAPI) and Lambda packaging |
| `dashboard/` | User-facing front end |
| `common/` | Shared code (e.g. `s3_paths.py`) used across ingestion/pipeline/ml |
| `infra/` | Terraform for AWS resources |
| `data/` | Local data cache (gitignored - never commit raw data) |
| `notebooks/` | Exploratory analysis, not production code |
| `docs/` | Architecture notes, decisions log |
| `tests/` | Unit/integration tests |

## Status / roadmap

- [x] Repo scaffold
- [x] S3 data lake layout + bucket structure (see `docs/data_lake_layout.md`)
- [x] Trace downloader script
- [x] Replay producer (simulated streaming ingestion)
- [x] Raw -> curated transforms
- [x] Feature engineering
- [ ] Baseline forecasting model + MLflow tracking
- [ ] Job-failure classification model (stretch)
- [ ] Model serving (Lambda + API Gateway)
- [ ] Dashboard
- [ ] Airflow orchestration
- [ ] Terraform IaC
- [ ] Monitoring / drift checks

## Setup

See `docs/architecture.md` for design decisions and `requirements/` for per-module dependencies. Setup instructions will be filled in as each component is built.

## License

MIT - see `LICENSE`.
