from datetime import date

from common.s3paths import (
    Category,
    Zone,
    dataset_path,
    features_path,
    models_path,
    athena_results_path,
)

def test_dataset_path_raw_events_with_variant():
    result = dataset_path(
        "my-bucket", Zone.RAW, Category.EVENTS, "pod_list", date(2026, 8, 15), variant="default" 
    )
    assert result == "s3://my-bucket/raw/events/pod_list/variant=default/dt=2026-08-15/"

def tests_dataset_path_curated_dimenstions_without_vairant():
    result = dataset_path(
        "my-bucket", Zone.CURATED, Category.DIMENSIONS, "node_list", date(2026, 8, 15)
    )
    assert result == "s3://my-bucket/curated/dimensions/node_list/dt=2026-08-15/"

def test_features_path():
    result = features_path("my-bucket", "gpu_demand_forecast", date(2026, 8, 15))
    assert result == "s3://my-bucket/features/gpu_demand_forecast/dt=2026-08-15/"

def test_models_path():
    result = models_path("my-bucket", "gpu_demand_forecast", "run123")
    assert result == "s3://my-bucket/models/gpu_demand_forecast/run123/"

def test_athena_results_path():
    assert athena_results_path("my-bucket") == "s3://my-bucket/athena-results/"