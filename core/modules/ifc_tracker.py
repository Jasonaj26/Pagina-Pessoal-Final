"""Module 10: IFC drawing handover tracker.

Flags downstream exposure where an Issued-For-Construction package is
late or missing relative to the construction activities that depend on
it. Driven by the user-configurable IFC package activity code type.
"""
from __future__ import annotations

import pandas as pd


def build_ifc_status(tasks: pd.DataFrame, warning_days: int, data_date: pd.Timestamp) -> pd.DataFrame:
    """Groups activities by their shared IFC package code, then compares the
    engineering (IFC issuance) side of that package against the
    construction/installation side of the *same* code - so downstream
    exposure is found via the activity-code linkage Jason sets up, not by
    guessing from activity names."""
    ifc_tasks = tasks[tasks["ifc_package_code"] != ""].copy()

    if ifc_tasks.empty:
        return pd.DataFrame(columns=[
            "package", "ifc_finish", "construction_start", "buffer_days", "status", "exposed_activities",
        ])

    rows = []
    for pkg, grp in ifc_tasks.groupby("ifc_package_code"):
        issuance = grp[grp["discipline"] != "Construction/Installation"]
        related_construction = grp[grp["discipline"] == "Construction/Installation"]

        ifc_finish = issuance["finish_display"].max() if not issuance.empty else grp["finish_display"].min()
        constr_start = related_construction["start_display"].min() if not related_construction.empty else pd.NaT

        buffer_days = (constr_start - ifc_finish).days if pd.notna(constr_start) and pd.notna(ifc_finish) else None
        all_complete = (issuance["status"] == "Complete").all() if not issuance.empty else False

        if all_complete:
            status = "green"
        elif buffer_days is None:
            status = "grey"
        elif buffer_days < 0:
            status = "red"
        elif buffer_days <= warning_days:
            status = "amber"
        else:
            status = "green"

        rows.append({
            "package": pkg,
            "ifc_finish": ifc_finish,
            "construction_start": constr_start,
            "buffer_days": buffer_days,
            "status": status,
            "exposed_activities": len(related_construction) if status in ("red", "amber") else 0,
        })
    return pd.DataFrame(rows).sort_values("ifc_finish")
