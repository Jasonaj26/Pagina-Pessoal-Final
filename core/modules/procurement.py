"""Module 11: Procurement & long-lead item tracker.

Same activity-code linkage pattern as the IFC tracker (Module 10): a
procurement package code applied to both the ordering/delivery activities
and the construction activities that need the item, so "at risk" can be
detected generically across any programme.
"""
from __future__ import annotations

import pandas as pd


def build_procurement_status(tasks: pd.DataFrame, at_risk_days: int) -> pd.DataFrame:
    proc_tasks = tasks[tasks["procurement_package_code"] != ""].copy()
    if proc_tasks.empty:
        return pd.DataFrame(columns=[
            "package", "order_start", "delivery_date", "need_by", "buffer_days", "status", "pct_complete",
        ])

    rows = []
    for pkg, grp in proc_tasks.groupby("procurement_package_code"):
        procurement_side = grp[grp["discipline"].isin(["Procurement", "Engineering"])]
        need_side = grp[grp["discipline"].isin(["Construction/Installation", "Commissioning"])]

        order_start = procurement_side["start_display"].min() if not procurement_side.empty else grp["start_display"].min()
        delivery_date = procurement_side["finish_display"].max() if not procurement_side.empty else grp["finish_display"].max()
        need_by = need_side["start_display"].min() if not need_side.empty else pd.NaT

        buffer_days = (need_by - delivery_date).days if pd.notna(need_by) and pd.notna(delivery_date) else None
        pct = procurement_side["pct_complete"].mean() if not procurement_side.empty else grp["pct_complete"].mean()

        if pct >= 100:
            status = "green"
        elif buffer_days is None:
            status = "grey"
        elif buffer_days < 0:
            status = "red"
        elif buffer_days <= at_risk_days:
            status = "amber"
        else:
            status = "green"

        rows.append({
            "package": pkg,
            "order_start": order_start,
            "delivery_date": delivery_date,
            "need_by": need_by,
            "buffer_days": buffer_days,
            "status": status,
            "pct_complete": pct,
        })
    return pd.DataFrame(rows).sort_values("delivery_date")
