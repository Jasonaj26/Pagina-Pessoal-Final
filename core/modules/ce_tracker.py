"""Module 13: NEC compensation event tracker.

Schedule-impact and status tracking only - explicitly no cost or value
tracking anywhere in this module. Links each CE's notified programme
impact (days) to whether a corresponding logic change actually exists in
the live programme, via the user-configured CE activity code.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

CE_REGISTER_COLUMNS = ["ce_number", "description", "status", "notified_impact_days", "date_notified"]


def summarize_ce(register: pd.DataFrame, live_tasks: pd.DataFrame, baseline_tasks: Optional[pd.DataFrame]) -> pd.DataFrame:
    if register.empty:
        return pd.DataFrame(columns=CE_REGISTER_COLUMNS + ["linked_in_live", "linked_in_baseline", "reflected_in_baseline", "flag_no_logic_change"])

    live_codes = set(live_tasks["ce_number"]) - {""} if live_tasks is not None and not live_tasks.empty else set()
    base_codes = set(baseline_tasks["ce_number"]) - {""} if baseline_tasks is not None and not baseline_tasks.empty else set()

    out = register.copy()
    out["notified_impact_days"] = pd.to_numeric(out["notified_impact_days"], errors="coerce").fillna(0)
    out["linked_in_live"] = out["ce_number"].isin(live_codes)
    out["linked_in_baseline"] = out["ce_number"].isin(base_codes)
    out["reflected_in_baseline"] = out["linked_in_baseline"]
    out["flag_no_logic_change"] = ~out["linked_in_live"]
    return out


def ce_headline_counts(ce_df: pd.DataFrame) -> dict:
    if ce_df.empty:
        return {"open": 0, "closed": 0, "impact_not_reflected_days": 0, "flagged_no_logic": 0}
    open_count = int((ce_df["status"].str.lower() == "open").sum())
    closed_count = int((ce_df["status"].str.lower() == "closed").sum())
    impact_not_reflected = float(ce_df.loc[~ce_df["reflected_in_baseline"], "notified_impact_days"].sum())
    flagged = int(ce_df["flag_no_logic_change"].sum())
    return {
        "open": open_count,
        "closed": closed_count,
        "impact_not_reflected_days": impact_not_reflected,
        "flagged_no_logic": flagged,
    }
