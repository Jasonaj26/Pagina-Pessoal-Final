"""Small generic CSV-backed store for the supplementary, editable tracker
data that doesn't live inside an XER (IFC issue dates, procurement delivery
status, CE register, key-date submission history, interface/constraint log).

Kept generic and activity-code driven: every tracker just needs an
`activity_code` column to cross-reference back into the loaded programme.
"""
from __future__ import annotations

import os

import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")


def _path(name: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}.csv")


def load_table(name: str, columns: list[str]) -> pd.DataFrame:
    path = _path(name)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            return df[columns]
        except (pd.errors.ParserError, OSError):
            pass
    return pd.DataFrame(columns=columns)


def save_table(name: str, df: pd.DataFrame) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(_path(name), index=False)
