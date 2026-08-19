import pytest

from ingestion.replay_producer import upload_node_list


def test_resolve_source_path_raises_if_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(upload_node_list, "NODE_LIST_PATH", tmp_path / "does_not_exist.csv")

    with pytest.raises(FileNotFoundError):
        upload_node_list.resolve_source_path()


def test_resolve_source_path_returns_path_when_present(monkeypatch, tmp_path):
    real_file = tmp_path / "openb_node_list_all_node.csv"
    real_file.write_text("sn,cpu_milli\n")
    monkeypatch.setattr(upload_node_list, "NODE_LIST_PATH", real_file)

    assert upload_node_list.resolve_source_path() == real_file