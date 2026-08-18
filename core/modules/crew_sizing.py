"""Module 4: Crew/gang sizing to hold P50.

Uses Jason's own production rate inputs (units per crew per day, entered
per discipline in Settings) and the remaining quantity of work he enters
for the current cycle - no assumed default rates anywhere.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

QUANTITY_COLUMNS = ["discipline", "remaining_quantity"]


def business_days_between(start: pd.Timestamp, end: pd.Timestamp) -> int:
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0
    return int(np.busday_count(start.date(), end.date()))


def required_crews(remaining_quantity: float, rate_per_crew_per_day: float, workdays_available: int) -> Optional[float]:
    if rate_per_crew_per_day is None or rate_per_crew_per_day <= 0:
        return None
    if workdays_available is None or workdays_available <= 0:
        return None
    if remaining_quantity is None or remaining_quantity <= 0:
        return 0.0
    return remaining_quantity / (rate_per_crew_per_day * workdays_available)


def build_crew_plan(quantities: pd.DataFrame, production_rates: dict, p50_date: pd.Timestamp, data_date: pd.Timestamp) -> pd.DataFrame:
    rows = []
    workdays = business_days_between(data_date, p50_date)
    for _, row in quantities.iterrows():
        disc = row["discipline"]
        qty = pd.to_numeric(row["remaining_quantity"], errors="coerce")
        qty = 0.0 if pd.isna(qty) else qty
        rate_info = production_rates.get(disc, {})
        rate = rate_info.get("rate_per_crew")
        unit = rate_info.get("unit", "")
        crews_exact = required_crews(qty, rate, workdays)
        rows.append({
            "discipline": disc,
            "remaining_quantity": qty,
            "unit": unit,
            "rate_per_crew_per_day": rate,
            "workdays_to_p50": workdays,
            "crews_required_exact": crews_exact,
            "crews_required": math.ceil(crews_exact) if crews_exact is not None else None,
        })
    return pd.DataFrame(rows)
