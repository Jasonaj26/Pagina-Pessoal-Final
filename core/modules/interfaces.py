"""Module 8: Generic interface & constraint tracker.

Driven entirely by the user-configurable activity code types
(settings: interface_activity_code_type / constraint_activity_code_type)
so the same logic works unchanged across any of Jason's programmes.
"""
from __future__ import annotations

import pandas as pd


def _status(row, data_date: pd.Timestamp) -> str:
    if row["status"] == "Complete":
        return "green"
    if pd.notna(row["finish_display"]) and row["finish_display"] < data_date:
        return "red"
    if row["total_float_days"] <= 0:
        return "amber"
    return "grey"


def build_tracker(tasks: pd.DataFrame, code_column: str, data_date: pd.Timestamp) -> pd.DataFrame:
    subset = tasks[tasks[code_column] != ""].copy()
    if subset.empty:
        return pd.DataFrame(columns=["task_code", "task_name", code_column, "discipline", "finish_display", "status", "total_float_days", "rag"])
    subset["rag"] = subset.apply(lambda r: _status(r, data_date), axis=1)
    cols = ["task_code", "task_name", code_column, "discipline", "finish_display", "status", "total_float_days", "rag"]
    return subset[cols].sort_values("finish_display")
