"""Module 9 (critical path Gantt) + Module 12 (programme health summary) -
combined on the landing page.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd


def select_critical_path_activities(tasks: pd.DataFrame, max_bars: int = 60) -> pd.DataFrame:
    critical = tasks[tasks["is_critical"] & tasks["start_display"].notna() & tasks["finish_display"].notna()].copy()
    if critical.empty:
        # fall back to lowest-float activities so the Gantt still shows something meaningful
        critical = tasks[tasks["start_display"].notna() & tasks["finish_display"].notna()].copy()
        critical = critical.sort_values("total_float_days").head(max_bars)
    else:
        critical = critical.sort_values("start_display").head(max_bars)
    # zero-duration bars (milestones) render as a sliver - pad slightly for visibility
    zero_dur = critical["finish_display"] <= critical["start_display"]
    critical.loc[zero_dur, "finish_display"] = critical.loc[zero_dur, "start_display"] + pd.Timedelta(hours=12)
    return critical


def select_key_date_milestones(tasks: pd.DataFrame) -> pd.DataFrame:
    return tasks[(tasks["key_date_code"] != "") & tasks["finish_display"].notna()].copy()


def compute_programme_health(dcma_metrics=None, mc_result=None, spi_overall: Optional[tuple] = None, key_date_status: Optional[pd.DataFrame] = None) -> dict:
    health = {}

    if dcma_metrics:
        from core.modules.dcma import summary_counts
        counts = summary_counts(dcma_metrics)
        scored = counts["green"] + counts["amber"] + counts["red"]
        health["dcma"] = {
            "counts": counts,
            "status": "red" if counts["red"] > 2 else ("amber" if counts["red"] > 0 or counts["amber"] > 3 else "green"),
            "label": f"{counts['green']}/{scored} passing",
        }
    else:
        health["dcma"] = {"counts": None, "status": "grey", "label": "Not run"}

    if mc_result is not None:
        p50 = mc_result.percentiles.get(50)
        p90 = mc_result.percentiles.get(90)
        spread = (p90 - p50).days if p50 is not None and p90 is not None else None
        status = "green"
        if spread is not None:
            status = "red" if spread > 60 else ("amber" if spread > 20 else "green")
        health["monte_carlo"] = {"p50": p50, "p90": p90, "spread": spread, "status": status}
    else:
        health["monte_carlo"] = {"p50": None, "p90": None, "spread": None, "status": "grey"}

    if spi_overall is not None:
        spi_count, spi_duration = spi_overall
        status = "grey"
        if pd.notna(spi_duration):
            status = "green" if spi_duration >= 0.95 else ("amber" if spi_duration >= 0.85 else "red")
        health["spi"] = {"spi_count": spi_count, "spi_duration": spi_duration, "status": status}
    else:
        health["spi"] = {"spi_count": None, "spi_duration": None, "status": "grey"}

    if key_date_status is not None and not key_date_status.empty:
        red = int((key_date_status["status"] == "red").sum())
        amber = int((key_date_status["status"] == "amber").sum())
        status = "red" if red > 0 else ("amber" if amber > 0 else "green")
        health["key_dates"] = {"red": red, "amber": amber, "total": len(key_date_status), "status": status}
    else:
        health["key_dates"] = {"red": 0, "amber": 0, "total": 0, "status": "grey"}

    statuses = [health[k]["status"] for k in health]
    if "red" in statuses:
        overall = "red"
    elif "amber" in statuses:
        overall = "amber"
    elif all(s == "grey" for s in statuses):
        overall = "grey"
    else:
        overall = "green"
    health["overall"] = overall
    return health
