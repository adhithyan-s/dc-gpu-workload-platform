
"""
Downloads the Alibaba GPU cluster trace source files (cluster-trace-gpu-v2023) to the local raw data cache (data/raw/).
 
This script only fetches the source files to disk - it does not touch S3.
See ingestion/replay_producer/ for the script that lands data in S3.
 
Usage:
    python -m ingestion.downloader.download_trace
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm

TRACE_BASE_URL = (
    "https://raw.githubusercontent.com/alibaba/clusterdata/master/"
    "cluster-trace-gpu-v2023/csv"
)

# Repo root is 3 levels up from this file: ingestion/downloader/download_trace.py
REPO_ROOT = Path(__file__).parents[2]
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class TraceFile:
    filename: str
    min_expected_bytes: int     # sanity floor - catches truncated/broken downloads

    @property
    def url(self) -> str:
        return f"{TRACE_BASE_URL}/{self.filename}"


TRACE_FILES = [
    TraceFile(filename="openb_node_list_all_node.csv", min_expected_bytes=40_000),
    TraceFile(filename="openb_pod_list_default.csv", min_expected_bytes=500_000),
]


def download_file(trace_file: TraceFile, dest_dir: Path) -> Path:
    dest_path = dest_dir / trace_file.filename
    response = requests.get(trace_file.url, stream=True, timeout=30)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    dest_dir.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "wb") as f, tqdm(
        total=total_size, unit="B", unit_scale=True, desc=trace_file.filename
    ) as progress:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            progress.update(len(chunk))

    return dest_path


def validate_download(dest_path: Path, trace_file: TraceFile) -> None:
    if not dest_path.exists():
        raise FileNotFoundError(f"{dest_path} was not created.")

    actual_size = dest_path.stat().st_size
    if actual_size < trace_file.min_expected_bytes:
        raise ValueError(
            f"{dest_path} is only {actual_size} bytes "
            f"(expected atleast {trace_file.min_expected_bytes}) - "
            "download may be truncated or the source may have changed."
        )


def main() -> None:
    print(f"Downloading trace files to {RAW_DATA_DIR}")
    for trace_file in TRACE_FILES:
        dest_path = download_file(trace_file, RAW_DATA_DIR)
        validate_download(dest_path, trace_file)
        print(f"OK: {dest_path} ({dest_path.stat().st_size:,} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()