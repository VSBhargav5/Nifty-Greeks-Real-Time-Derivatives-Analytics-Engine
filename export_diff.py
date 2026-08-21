"""Write a snapshot-diff as CSV (headlines + movers)."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import pandas as pd


def diff_to_csv(diff: dict[str, Any], movers: pd.DataFrame | None = None) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["key", "value"])
    for k, v in diff.items():
        writer.writerow([k, v])
    if movers is not None and not movers.empty:
        writer.writerow([])
        writer.writerow(list(movers.columns))
        for row in movers.itertuples(index=False):
            writer.writerow(list(row))
    return buf.getvalue()


def write_diff_csv(
    path: Path,
    diff: dict[str, Any],
    movers: pd.DataFrame | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diff_to_csv(diff, movers), encoding="utf-8")
