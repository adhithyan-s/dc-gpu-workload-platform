# Architecture & Decisions Log

Running log of key design decisions, so the reasoning is documented alongside the code (and reusable for interviews / CV write-ups).

## Dataset

**Chosen:** Alibaba `cluster-trace-gpu-v2023`
(https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2023)

- Real production traces: ~6,200 GPUs across ~1,200 machines, heterogeneous AI/ML workloads.
- Distributed as plain downloadable CSV files (no query-engine gate) - allows a direct-to-S3 ingestion pipeline.

**Considered and rejected:**
- *Google cluster-trace 2019*  richer schema, but Google only distributes it via BigQuery (2.4TiB, not downloadable). Would have forced a GCP dependency just to extract data, and free-tier BigQuery query quotas add operational risk (accidental full-table scans).
- *Google cluster-trace 2011* - downloadable, but older and much less rich (no CPU histograms, no alloc-set info).

## Ingestion pattern: simulated streaming replay

The source data is static (a historical trace), but production data center telemetry is continuous. Rather than a one-shot batch download, ingestion is built as a **replay producer**: a script that reads the trace in timestamp order and emits it at a controlled pace into Kinesis (or a scheduled Lambda), so the rest of the pipeline is built and tested against a realistic streaming source rather than a static file. This is a standard technique for testing streaming systems without a live production feed.

## Cost constraints

Everything is designed to run within the AWS free tier:
- S3 for storage (raw/interim/processed layers)
- Lambda + API Gateway for serving (near-zero cost at low request volume)
- EventBridge for scheduling instead of a long-running orchestrator host
- Athena (serverless, pay-per-query) preferred over a persistent Spark/EMR cluster for transforms where possible

Decisions that trade off some "real-time-ness" for cost will be noted here as they come up.

## Open questions / next decisions

- Exact S3 bucket / prefix layout (next step)
- Kinesis vs. scheduled Lambda for the replay producer
- Orchestration: local Airflow (Docker) vs. lighter-weight scheduler
