"""
Central definitions for the S3 data lake layout, so no other module hardcodes prefix strings. See docs/data_lake_layout.md for the full design rationale.
 
Zones (medallion architecture):
    raw/             bronze - immutable, as-ingested data
    curated/         silver - cleaned, typed, deduplicated
    features/        gold - model-ready aggregates
    models/          MLflow artifact store
    athena-results/  Athena query scratch space (lifecycle: expires after 7 days)
 
Within raw/ and curated/, data is further split by whether it's a slowly changing DIMENSION (e.g. node/cluster topology, loaded rarely) or an EVENTS/fact table (e.g. pod scheduling events, continuously replayed).
"""

from __future__ import annotations

from datetime import date
from enum import Enum

class Zone(str, Enum):
    RAW = "raw"
    CURATED = "curated"
    FEATURES = "features"
    MODELS = "models"
    ATHENA_RESULTS = "athena-results"

class Category(str, Enum):
    DIMENSIONS = "dimensions"
    EVENTS = "events"

def dataset_path(
        bucket: str,
        zone: Zone,
        category: Category,
        dataset: str,
        dt: date,
        variant: str | None = None,
) -> str:
    """
    Build a partitioned S3 URI for a raw or curated dataset.
 
    >>> dataset_path("my-bucket", Zone.RAW, Category.EVENTS, "pod_list", date(2026, 8, 15), variant="default")
    's3://my-bucket/raw/events/pod_list/variant=default/dt=2026-08-15/'
    """

    parts = [zone.value, category.value, dataset]
    if variant:
        parts.append(f"variant={variant}")
    parts.append(f"dt={dt.isoformat()}")

    return f"s3://{bucket}/" + "/".join(parts) + "/"

def features_path(
        bucket: str,
        feature_set: str,
        dt: date,
) -> str:
    """
    >>> features_path("my-bucket", "gpu_demand_forecast", date(2026, 8, 15))
    's3://my-bucket/features/gpu_demand_forecast/dt=2026-08-15/'
    """
    return f"s3://{bucket}/{Zone.FEATURES.value}/{feature_set}/dt={dt.isoformat()}/"

def models_path(
        bucket: str,
        experiment: str,
        run_id: str,
) -> str:
    """
    >>> models_path("my-bucket", "gpu-demand-forecast", "run123")
    's3://my-bucket/models/gpu-demand-forecast/run123/'
    """
    return f"s3://{bucket}/{Zone.MODELS.value}/{experiment}/{run_id}/"

def athena_results_path(bucket: str) -> str:
    """
    >>> athena_results_path("my-bucket")
    's3://my-bucket/athena-results/'
    """
    return f"s3://{bucket}/{Zone.ATHENA_RESULTS.value}/"
