import pandas as pd

from ingestion.replay_producer.replay_pod_events import build_batches

def _sample_df():
    return pd.DataFrame(
        {
            "name": [f"pod-{i}" for i in range(10)],
            "creation_time": [0, 5, 10, 15, 20, 50, 80, 95, 99, 100],
        }
    )


def test_build_batches_covers_every_row_exactly_once():
    df = _sample_df()
    batches = build_batches(df, num_batches=5)

    total_rows = sum(len(b) for b in batches)
    assert total_rows == len(df)

    all_names = sorted(name for b in batches for name in b["name"])
    assert all_names == sorted(df["name"])


def test_build_batches_returns_requested_number_of_batches():
    df = _sample_df()
    batches = build_batches(df, num_batches=5)
    assert len(batches) == 5


def test_build_batches_last_window_includes_max_value():
    df = _sample_df()
    batches = build_batches(df, num_batches=5)
    assert 100 in batches[-1]["creation_time"].values


def test_build_batches_handels_empty_windows():
    # a big gap between 0 and 1000 means several middle windows will be empty
    df = pd.DataFrame({"name": ["a", "b"], "creation_time": [0, 1000]})
    batches = build_batches(df, num_batches=10)
 
    assert sum(len(b) for b in batches) == 2
    assert any(len(b) == 0 for b in batches)  # at least one empty window