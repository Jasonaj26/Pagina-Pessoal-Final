"""Cycle-on-cycle history recorder.

Every time Jason loads a new live XER (with a baseline already cached),
we snapshot a handful of summary metrics keyed by that cycle's data date.
This is what powers the genuine trend charts in Module 5 (SPI trend) and
Module 7 (key date trend) - built from Jason's own successive submissions
rather than fabricated history. A single cycle just shows one point; the
trend fills in as more cycles are loaded over time.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from core.store import load_table, save_table

PROGRAMME_HISTORY_COLUMNS = [
    "data_date", "live_filename", "spi_count_overall", "spi_duration_overall",
    "dcma_green", "dcma_amber", "dcma_red",
]
KEY_DATE_HISTORY_COLUMNS = ["data_date", "key_date_name", "forecast_date", "baseline_date"]


def _spi(tasks: pd.DataFrame, baseline_tasks: pd.DataFrame, data_date: pd.Timestamp) -> tuple[float, float]:
    from core.modules.spi import compute_spi_overall
    return compute_spi_overall(tasks, baseline_tasks, data_date)


def record_cycle_snapshot(tasks: pd.DataFrame, baseline_tasks: Optional[pd.DataFrame], settings: dict, data_date: pd.Timestamp, live_filename: str) -> None:
    if baseline_tasks is None or baseline_tasks.empty or tasks.empty:
        return

    from core.modules.dcma import run_dcma_assessment, summary_counts
    from core.tasks import build_relationships  # noqa: avoid circular import at module load

    spi_count, spi_duration = _spi(tasks, baseline_tasks, data_date)

    hist = load_table("programme_history", PROGRAMME_HISTORY_COLUMNS)
    date_str = data_date.strftime("%Y-%m-%d")
    hist = hist[hist["data_date"] != date_str]
    new_row = {
        "data_date": date_str,
        "live_filename": live_filename,
        "spi_count_overall": f"{spi_count:.4f}",
        "spi_duration_overall": f"{spi_duration:.4f}",
        "dcma_green": "",
        "dcma_amber": "",
        "dcma_red": "",
    }
    hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)
    save_table("programme_history", hist)

    key_dates = tasks[tasks["key_date_code"] != ""]
    if not key_dates.empty:
        kd_hist = load_table("key_date_history", KEY_DATE_HISTORY_COLUMNS)
        base_by_name = dict(zip(
            baseline_tasks[baseline_tasks["key_date_code"] != ""]["key_date_code"],
            baseline_tasks[baseline_tasks["key_date_code"] != ""]["finish_display"],
        ))
        rows = []
        for _, row in key_dates.iterrows():
            kd_hist = kd_hist[~((kd_hist["data_date"] == date_str) & (kd_hist["key_date_name"] == row["key_date_code"]))]
            base_date = base_by_name.get(row["key_date_code"])
            rows.append({
                "data_date": date_str,
                "key_date_name": row["key_date_code"],
                "forecast_date": row["finish_display"].strftime("%Y-%m-%d") if pd.notna(row["finish_display"]) else "",
                "baseline_date": base_date.strftime("%Y-%m-%d") if base_date is not None and pd.notna(base_date) else "",
            })
        kd_hist = pd.concat([kd_hist, pd.DataFrame(rows)], ignore_index=True)
        save_table("key_date_history", kd_hist)


def load_programme_history() -> pd.DataFrame:
    df = load_table("programme_history", PROGRAMME_HISTORY_COLUMNS)
    if df.empty:
        return df
    df["data_date"] = pd.to_datetime(df["data_date"], errors="coerce")
    df["spi_count_overall"] = pd.to_numeric(df["spi_count_overall"], errors="coerce")
    df["spi_duration_overall"] = pd.to_numeric(df["spi_duration_overall"], errors="coerce")
    return df.sort_values("data_date")


def load_key_date_history() -> pd.DataFrame:
    df = load_table("key_date_history", KEY_DATE_HISTORY_COLUMNS)
    if df.empty:
        return df
    df["data_date"] = pd.to_datetime(df["data_date"], errors="coerce")
    df["forecast_date"] = pd.to_datetime(df["forecast_date"], errors="coerce")
    df["baseline_date"] = pd.to_datetime(df["baseline_date"], errors="coerce")
    return df.sort_values(["key_date_name", "data_date"])
