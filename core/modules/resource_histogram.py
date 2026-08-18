"""Module 6: Aggregate resource histogram.

Uses real TASKRSRC budgeted quantities when the XER export includes
resource assignments; otherwise falls back to a concurrent-activity-count
proxy per discipline (clearly labelled as such) so the module still works
on exports that don't carry resource loading.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd


def _col(df: pd.DataFrame, *names: str) -> Optional[str]:
    for n in names:
        if n in df.columns:
            return n
    return None


def has_resource_data(result) -> bool:
    return not result.table("TASKRSRC").empty


def _spread_daily(rows: list[tuple[pd.Timestamp, pd.Timestamp, str, float]]) -> pd.DataFrame:
    frames = []
    for start, finish, discipline, qty in rows:
        if pd.isna(start) or pd.isna(finish) or finish < start:
            continue
        dates = pd.date_range(start.normalize(), finish.normalize(), freq="D")
        if len(dates) == 0:
            continue
        daily_qty = qty / len(dates)
        frames.append(pd.DataFrame({"date": dates, "discipline": discipline, "qty": daily_qty}))
    if not frames:
        return pd.DataFrame(columns=["date", "discipline", "qty"])
    return pd.concat(frames, ignore_index=True)


def compute_resource_histogram(tasks: pd.DataFrame, result, period: str = "W") -> tuple[pd.DataFrame, bool]:
    """Returns (long-format [period, discipline, demand] DataFrame, used_real_resource_data)."""
    active = tasks[tasks["status"] != "Complete"].copy()
    active = active[active["start_display"].notna() & active["finish_display"].notna()]

    if has_resource_data(result):
        taskrsrc = result.table("TASKRSRC")
        qty_col = _col(taskrsrc, "remain_qty", "target_qty")
        task_id_col = _col(taskrsrc, "task_id")
        if qty_col and task_id_col:
            merged = taskrsrc[[task_id_col, qty_col]].rename(columns={task_id_col: "task_id", qty_col: "qty"})
            merged["task_id"] = merged["task_id"].astype(str)
            merged["qty"] = pd.to_numeric(merged["qty"], errors="coerce").fillna(0)
            joined = active.merge(merged, on="task_id", how="inner")
            rows = list(zip(joined["start_display"], joined["finish_display"], joined["discipline"], joined["qty"]))
            daily = _spread_daily(rows)
            used_real = True
        else:
            daily = pd.DataFrame()
            used_real = False
    else:
        used_real = False
        daily = pd.DataFrame()

    if daily.empty:
        rows = list(zip(active["start_display"], active["finish_display"], active["discipline"], [1.0] * len(active)))
        daily = _spread_daily(rows)
        used_real = False

    if daily.empty:
        return pd.DataFrame(columns=["period", "discipline", "demand"]), used_real

    daily["period"] = daily["date"].dt.to_period(period).dt.start_time
    agg = daily.groupby(["period", "discipline"], as_index=False)["qty"].sum().rename(columns={"qty": "demand"})
    return agg, used_real


def flag_over_allocation(histogram: pd.DataFrame, capacity_by_discipline: dict) -> pd.DataFrame:
    if histogram.empty or not capacity_by_discipline:
        histogram = histogram.copy()
        histogram["over_allocated"] = False
        return histogram
    histogram = histogram.copy()
    histogram["capacity"] = histogram["discipline"].map(capacity_by_discipline)
    histogram["over_allocated"] = histogram["capacity"].notna() & (histogram["demand"] > histogram["capacity"])
    return histogram
