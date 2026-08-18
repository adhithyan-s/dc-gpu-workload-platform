import pytest

from ingestion.downloader.download_trace import TraceFile, validate_download

def test_trace_file_url_property():
    tf = TraceFile(filename="openb_node_list_all_node.csv", min_expected_bytes=40_000)
    assert tf.url == (
        "https://raw.githubusercontent.com/alibaba/clusterdata/master/"
        "cluster-trace-gpu-v2023/csv/openb_node_list_all_node.csv"
    ) 


def test_validate_download_raises_if_file_missing(tmp_path):
    tf = TraceFile(filename="missing.csv", min_expected_bytes=100)
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        validate_download(missing_path, tf)


def test_validate_download_raises_if_file_too_small(tmp_path):
    tf = TraceFile(filename="tiny.csv", min_expected_bytes=1000)
    tiny_path = tmp_path / "tiny.csv"
    tiny_path.write_bytes(b"not enough bytes")

    with pytest.raises(ValueError):
        validate_download(tiny_path, tf)


def test_validate_download_passes_for_large_enough_files(tmp_path):
    tf = TraceFile(filename="ok.csc", min_expected_bytes=10)
    ok_path = tmp_path / "ok.csv"
    ok_path.write_bytes(b"x" * 50)

    validate_download(ok_path, tf)