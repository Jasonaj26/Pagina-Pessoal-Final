"""Module 5: Schedule Performance Index by discipline.

SPI calculated two ways, both against the loaded baseline:
  - activity-count SPI = activities complete ÷ activities baselined to be complete by the data date
  - duration-weighted SPI = planned duration of completed activities ÷ planned duration of
    activities baselined to be complete by the data date
"""
from __future__ import annotations

from typing import Optional

import pandas as pd


def _planned_to_date(tasks: pd.DataFrame, baseline_tasks: pd.DataFrame, data_date: pd.Timestamp) -> pd.DataFrame:
    merged = tasks.merge(
        baseline_tasks[["task_code", "finish_planned", "duration_planned_days"]],
        on="task_code", how="inner", suffixes=("", "_base"),
    )
    return merged[(merged["finish_planned_base"].notna()) & (merged["finish_planned_base"] <= data_date)]


def compute_spi_overall(tasks: pd.DataFrame, baseline_tasks: pd.DataFrame, data_date: pd.Timestamp) -> tuple[float, float]:
    if tasks.empty or baseline_tasks.empty:
        return (float("nan"), float("nan"))
    planned = _planned_to_date(tasks, baseline_tasks, data_date)
    if planned.empty:
        return (1.0, 1.0)
    complete = planned[planned["status"] == "Complete"]
    spi_count = len(complete) / max(len(planned), 1)
    spi_duration = complete["duration_planned_days_base"].sum() / max(planned["duration_planned_days_base"].sum(), 1e-9)
    return (spi_count, spi_duration)


def compute_spi_by_discipline(tasks: pd.DataFrame, baseline_tasks: pd.DataFrame, data_date: pd.Timestamp) -> pd.DataFrame:
    if tasks.empty or baseline_tasks.empty:
        return pd.DataFrame()
    planned = _planned_to_date(tasks, baseline_tasks, data_date)
    if planned.empty:
        return pd.DataFrame()

    rows = []
    for disc, grp in planned.groupby("discipline"):
        complete = grp[grp["status"] == "Complete"]
        not_complete = grp[grp["status"] != "Complete"]
        spi_count = len(complete) / max(len(grp), 1)
        spi_duration = complete["duration_planned_days_base"].sum() / max(grp["duration_planned_days_base"].sum(), 1e-9)
        sv_count = len(not_complete)
        slip_days = (data_date - not_complete["finish_planned_base"]).dt.days.clip(lower=0)
        sv_days = float(slip_days.sum())
        rows.append({
            "discipline": disc,
            "planned_to_date": len(grp),
            "complete": len(complete),
            "spi_count": spi_count,
            "spi_duration": spi_duration,
            "sv_count": sv_count,
            "sv_days": sv_days,
        })
    return pd.DataFrame(rows).sort_values("discipline")
