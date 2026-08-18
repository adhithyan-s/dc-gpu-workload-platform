# Architecture & Decisions Log

Running log of key design decisions, so the reasoning is documented alongside the code (and reusable for interviews / CV write-ups).

## Dataset

**Chosen:** Alibaba `cluster-trace-gpu-v2023`
(https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2023)

- Real production traces: ~6,200 GPUs across ~1,200 machines, heterogeneous AI/ML workloads.
- Distributed as plain downloadable CSV files (no query-engine gate) - allows a direct-to-S3 ingestion pipeline.

**Considered and rejected:**
- *Google cluster-trace 2019* - richer schema, but Google only distributes it via BigQuery (2.4TiB, not downloadable). Would have forced a GCP dependency just to extract data, and free-tier BigQuery query quotas add operational risk (accidental full-table scans).
- *Google cluster-trace 2011* - downloadable, but older and much less rich (no CPU histograms, no alloc-set info).

## Ingestion pattern: simulated streaming replay

The source data is static (a historical trace), but production data center telemetry is continuous. Rather than a one-shot batch download, ingestion is built as a **replay producer**: a script that reads the trace in timestamp order and writes it as timestamped micro-batch files straight to S3 at a controlled pace, so the rest of the pipeline is built and tested against a realistic streaming source rather than a static file. This is a standard technique for testing streaming systems without a live production feed.

**Decided against Kinesis.** Considered using Kinesis Data Streams to carry
the replayed events instead of writing directly to S3. Rejected because:
- Kinesis bills per shard-hour even when idle - it isn't part of AWS's always-free tier (only a limited 12-month promotional allowance), which conflicts with the project's minimum-cost goal.
- It solves a problem this project doesn't have: sub-second delivery to multiple concurrent live consumers. A dashboard refreshing every few minutes doesn't need that, and writing directly to S3 still demonstrates the same core skill (event-time-ordered, incremental ingestion) at zero ongoing cost.

**Replay design specifics:**
- The real trace's `pod_list` creation events are extremely bursty - almost no activity in the first ~114 of 149 days, then ~8,100 of 8,152 pods created in the final ~35 days. The replay preserves this distribution rather than smoothing it into an artificial steady trickle, since a pipeline that only survives uniform load isn't a realistic test.
- The 149-day trace is time-compressed into a short wall-clock run (exact duration configurable), split into a fixed number of time-windows; `creation_time = 0` is anchored to the moment the script starts.
- Defaults to a dry run (prints what it would upload) - writing to AWS requires an explicit opt-in flag.

## Cost constraints

Everything is designed to run within the AWS free tier:
- S3 for storage (raw/interim/processed layers)
- Lambda + API Gateway for serving (near-zero cost at low request volume)
- EventBridge for scheduling instead of a long-running orchestrator host
- Athena (serverless, pay-per-query) preferred over a persistent Spark/EMR cluster for transforms where possible

Decisions that trade off some "real-time-ness" for cost will be noted here as they come up.

## S3 data lake layout

Decided - full design and rationale in `docs/data_lake_layout.md`. Summary: single bucket, prefix-partitioned by medallion zone (`raw/` -> `curated/` -> `features/`), with `raw/` and `curated/` further split into `dimensions/` (node topology, loaded once) vs `events/` (pod scheduling data, the actual replay stream). Partitioned by ingestion date (`dt=`), not trace-internal time, to mirror how a real streaming pipeline lands data. Provisioned via `infra/terraform/`.

## Open questions / next decisions

- Orchestration: local Airflow (Docker) vs. lighter-weight scheduler