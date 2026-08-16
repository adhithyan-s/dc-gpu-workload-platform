# S3 Data Lake Layout

## Design

Single bucket, prefix-partitioned by zone (medallion architecture) rather than one bucket per zone. For this scale of project a single bucket with clear prefixes is easier to secure and manage than five small buckets, and S3 doesn't charge or perform differently either way. (At real organizational scale, splitting into per-zone or per-environment buckets for stricter IAM boundaries is the more common pattern - noted here as the production-grade alternative, not because this project needs it.)

```
s3://<bucket>/
├── raw/                                  # bronze - immutable, as-ingested
│   ├── dimensions/
│   │   └── node_list/
│   │       └── variant=all_node/dt=YYYY-MM-DD/*.csv
│   └── events/
│       └── pod_list/
│           └── variant=default/dt=YYYY-MM-DD/*.csv
│
├── curated/                              # silver - cleaned, typed, deduped
│   ├── dimensions/
│   │   └── node_list/variant=all_node/dt=YYYY-MM-DD/*.parquet
│   └── events/
│       └── pod_list/variant=default/dt=YYYY-MM-DD/*.parquet
│
├── features/                             # gold - model-ready aggregates
│   └── gpu_demand_forecast/dt=YYYY-MM-DD/*.parquet
│
├── models/                               # MLflow artifact store
│   └── <experiment>/<run_id>/
│
└── athena-results/                       # Athena query scratch space
                                           # (lifecycle: expires after 7 days)
```

## Why dimensions vs. events

The trace splits naturally into two kinds of data, and the layout reflects that on purpose:

- **`dimensions/`** - `node_list` describes the cluster's machines (CPU/memory/GPU capacity per node). It's a slowly-changing snapshot, not a time series - <cite index="70-1">it lists 1523 nodes with their CPU, main memory, GPU specifications and GPU types</cite>. It's loaded once (or on the rare occasion the topology changes), not replayed.
- **`events/`** - `pod_list` is the actual fact table: <cite index="70-1">8152 tasks submitted to the GPU cluster, with resource specifications, QoS, phase, and creation/deletion/scheduled timestamps</cite>. This is what the replay producer streams - each pod's `creation_time` becomes the moment it "arrives" in the pipeline.

This is standard star-schema thinking (dimension vs. fact tables) applied to a data lake instead of a warehouse - same idea, worth knowing either way.

## Partitioning

- Partition key is `dt=` = **ingestion date** (the date the replay producer wrote the record), not the trace's internal relative timestamp. This matches how a real streaming pipeline partitions data - by arrival time - while the trace's own `creation_time` / `scheduled_time` / `deletion_time` stay as ordinary columns inside the data for feature engineering.
- `variant=` partitions the different pod_list samples (`default`, `cpu100`, `gpushare20`, `gpuspec33`) so Athena can query one workload slice without scanning the others.

## File formats

- `raw/` keeps the exact format the data arrives in (CSV) - immutable source of truth, never rewritten.
- `curated/` and `features/` convert to **Parquet + Snappy** - columnar, compressed, and what Athena/Spark actually want to query efficiently.

## Cost / lifecycle notes

- Total raw data here is tens of MB, not GB - comfortably inside S3's free tier (5GB standard storage for 12 months), so no Glacier/cold-tier transition is needed for this project (would be a real consideration at production scale).
- `athena-results/` gets a **7-day expiration lifecycle rule** - Athena writes a results file on every query and this prefix otherwise grows forever for no benefit.
- Bucket has **public access fully blocked** and **default SSE-S3 encryption** - free, and the kind of default a reviewer would expect to see.

## Clarification: why raw/ mirrors the source instead of pre-modeling

It might look odd that raw/ already has separate node_list and pod_list paths - doesn't a DE project extract fact/dim tables from raw data itself?

The short answer: raw/ is faithful to the *source system's* schema, which already exports these as two files (Alibaba's own internal tables) - same as pulling separate tables from a production Postgres DB. That's what "raw" means: unmodified as delivered, not un-modeled.

The actual star-schema design work (surrogate keys, normalized dimensions pulled out of pod_list's qos/gpu_spec/pod_phase columns, a clean fact_pod_events table) happens as a curated/ transform - planned but not yet built. See pipeline/transforms/ once that lands.

## What's still open

- Whether Athena is used for `curated/` transforms directly, or PySpark reads/writes the same layout - decided when we build `pipeline/transforms/`.
- MLflow's artifact store target (`models/` prefix vs. MLflow's own default) - decided when we build `ml/training/`.