from __future__ import annotations
import os
from typing import Iterable, Dict, Any
import pyarrow as pa
import pyarrow.parquet as pq

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data", "parquet"))


def write_events(dataset: str, rows: Iterable[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    table = pa.Table.from_pylist(list(rows))
    pq.write_to_dataset(table, root_path=os.path.join(DATA_DIR, dataset))
