"""Module 7: Key date cycle-on-cycle trend tracking."""
from __future__ import annotations

import pandas as pd


def compute_key_date_status(tasks: pd.DataFrame, baseline_tasks: pd.DataFrame, amber_days: int, red_days: int) -> pd.DataFrame:
    key_dates = tasks[tasks["key_date_code"] != ""][["key_date_code", "finish_display"]].rename(
        columns={"key_date_code": "key_date_name", "finish_display": "forecast_date"}
    )
    if key_dates.empty:
        return pd.DataFrame(columns=["key_date_name", "forecast_date", "baseline_date", "variance_days", "status"])

    base = pd.DataFrame(columns=["key_date_name", "baseline_date"])
    if baseline_tasks is not None and not baseline_tasks.empty:
        base = baseline_tasks[baseline_tasks["key_date_code"] != ""][["key_date_code", "finish_display"]].rename(
            columns={"key_date_code": "key_date_name", "finish_display": "baseline_date"}
        )

    merged = key_dates.merge(base, on="key_date_name", how="left")
    merged["variance_days"] = (merged["forecast_date"] - merged["baseline_date"]).dt.days

    def status_for(v):
        if pd.isna(v):
            return "grey"
        if v <= 0:
            return "green"
        if v <= amber_days:
            return "amber"
        return "red"

    merged["status"] = merged["variance_days"].apply(status_for)
    return merged.sort_values("forecast_date")


def consecutive_slip_flags(key_date_history: pd.DataFrame) -> pd.DataFrame:
    """For each key date, how many consecutive most-recent cycles slipped later than the prior cycle."""
    if key_date_history.empty:
        return pd.DataFrame(columns=["key_date_name", "consecutive_slips"])

    results = []
    for name, grp in key_date_history.groupby("key_date_name"):
        grp = grp.sort_values("data_date")
        forecasts = grp["forecast_date"].tolist()
        streak = 0
        for i in range(len(forecasts) - 1, 0, -1):
            if pd.isna(forecasts[i]) or pd.isna(forecasts[i - 1]):
                break
            if forecasts[i] > forecasts[i - 1]:
                streak += 1
            else:
                break
        results.append({"key_date_name": name, "consecutive_slips": streak})
    return pd.DataFrame(results)
