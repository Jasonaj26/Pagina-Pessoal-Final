"""Module 2: DCMA 14-Point Assessment.

Implements the standard DCMA 14-point schedule health check. Thresholds
are all sourced from settings (core.settings, editable on the Settings
page) rather than hardcoded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class DcmaMetric:
    number: int
    name: str
    description: str
    result_display: str
    threshold_display: str
    status: str  # "green" | "amber" | "red" | "grey"
    failing_ids: List[str] = field(default_factory=list)
    note: str = ""


def _status(value: float, max_allowed: float, invert: bool = False) -> str:
    """invert=True means higher-is-better (value must be >= max_allowed to pass)."""
    if invert:
        if value >= max_allowed:
            return "green"
        if value >= max_allowed * 0.9:
            return "amber"
        return "red"
    if value <= max_allowed:
        return "green"
    if value <= max_allowed * 1.5:
        return "amber"
    return "red"


def run_dcma_assessment(
    tasks: pd.DataFrame,
    relationships: pd.DataFrame,
    thresholds: dict,
    baseline_tasks: Optional[pd.DataFrame] = None,
    data_date: Optional[pd.Timestamp] = None,
) -> List[DcmaMetric]:
    metrics: List[DcmaMetric] = []
    detail = tasks[(tasks["task_type"] == "TT_Task") | (tasks["task_type"] == "")].copy()
    if detail.empty:
        detail = tasks[~tasks["is_milestone"]].copy()
    total_detail = max(len(detail), 1)
    data_date = data_date or pd.Timestamp.today()

    has_pred = set(relationships["task_id"]) if not relationships.empty else set()
    has_succ = set(relationships["pred_task_id"]) if not relationships.empty else set()

    # ---- 1. Logic (missing predecessor AND/OR successor) -----------------
    incomplete = detail[detail["status"] != "Complete"]
    missing_logic = incomplete[~incomplete["task_id"].isin(has_pred) | ~incomplete["task_id"].isin(has_succ)]
    pct = 100 * len(missing_logic) / max(len(incomplete), 1)
    metrics.append(DcmaMetric(
        1, "Logic", "% of incomplete activities missing a predecessor and/or successor",
        f"{pct:.1f}%", f"≤ {thresholds['logic_missing_pct_max']}%",
        _status(pct, thresholds["logic_missing_pct_max"]),
        missing_logic["task_code"].tolist(),
    ))

    # ---- 2. Leads (negative lag) ------------------------------------------
    leads = relationships[relationships["lag_days"] < 0] if not relationships.empty else pd.DataFrame()
    metrics.append(DcmaMetric(
        2, "Leads", "Count of relationships with negative lag (leads)",
        f"{len(leads)}", f"= {thresholds['leads_count_max']}",
        _status(len(leads), thresholds["leads_count_max"]),
        tasks[tasks["task_id"].isin(leads["task_id"])]["task_code"].tolist() if not leads.empty else [],
    ))

    # ---- 3. Lags (positive lag) --------------------------------------------
    lags = relationships[relationships["lag_days"] > 0] if not relationships.empty else pd.DataFrame()
    pct_lag = 100 * len(lags) / max(len(relationships), 1)
    metrics.append(DcmaMetric(
        3, "Lags", "% of relationships with positive lag",
        f"{pct_lag:.1f}% ({len(lags)})", f"≤ {thresholds['lags_count_max']}%",
        _status(pct_lag, thresholds["lags_count_max"]),
        tasks[tasks["task_id"].isin(lags["task_id"])]["task_code"].tolist() if not lags.empty else [],
    ))

    # ---- 4. Relationship types (FS) ----------------------------------------
    fs = relationships[relationships["type"].str.upper() == "PR_FS"] if not relationships.empty else pd.DataFrame()
    pct_fs = 100 * len(fs) / max(len(relationships), 1)
    metrics.append(DcmaMetric(
        4, "Relationship Types", "% of relationships that are Finish-to-Start",
        f"{pct_fs:.1f}%", f"≥ {thresholds['fs_relationship_pct_min']}%",
        _status(pct_fs, thresholds["fs_relationship_pct_min"], invert=True),
    ))

    # ---- 5. Hard Constraints -------------------------------------------------
    hard_types = {"CS_MSO", "CS_MSOB", "CS_MEO", "CS_MEOA", "CS_MANDFIN", "CS_MANDSTART"}
    hard = detail[detail["constraint_type"].isin(hard_types)]
    metrics.append(DcmaMetric(
        5, "Hard Constraints", "Count of activities with a hard constraint (must start/finish on, mandatory)",
        f"{len(hard)}", f"≤ {thresholds['hard_constraints_count_max']}",
        _status(len(hard), thresholds["hard_constraints_count_max"]),
        hard["task_code"].tolist(),
    ))

    # ---- 6. High Float --------------------------------------------------------
    high_float = detail[detail["total_float_days"] > thresholds["high_float_days"]]
    pct_hf = 100 * len(high_float) / total_detail
    metrics.append(DcmaMetric(
        6, "High Float", f"% of activities with total float > {thresholds['high_float_days']} days",
        f"{pct_hf:.1f}%", f"≤ {thresholds['high_float_pct_max']}%",
        _status(pct_hf, thresholds["high_float_pct_max"]),
        high_float["task_code"].tolist(),
    ))

    # ---- 7. Negative Float -------------------------------------------------
    neg_float = detail[detail["total_float_days"] < 0]
    metrics.append(DcmaMetric(
        7, "Negative Float", "Count of activities with negative total float",
        f"{len(neg_float)}", f"= {thresholds['negative_float_count_max']}",
        _status(len(neg_float), thresholds["negative_float_count_max"]),
        neg_float["task_code"].tolist(),
    ))

    # ---- 8. High Duration ----------------------------------------------------
    high_dur = detail[detail["duration_planned_days"] > thresholds["high_duration_days"]]
    pct_hd = 100 * len(high_dur) / total_detail
    metrics.append(DcmaMetric(
        8, "High Duration", f"% of activities with planned duration > {thresholds['high_duration_days']} working days",
        f"{pct_hd:.1f}%", f"≤ {thresholds['high_duration_pct_max']}%",
        _status(pct_hd, thresholds["high_duration_pct_max"]),
        high_dur["task_code"].tolist(),
    ))

    # ---- 9. Invalid Dates -------------------------------------------------
    future_actual_start = detail[detail["start_actual"] > data_date]
    future_actual_finish = detail[detail["finish_actual"] > data_date]
    past_forecast = detail[(detail["status"] != "Complete") & (detail["finish_early"] < data_date) & detail["finish_early"].notna()]
    invalid = pd.concat([future_actual_start, future_actual_finish, past_forecast]).drop_duplicates(subset="task_id")
    metrics.append(DcmaMetric(
        9, "Invalid Dates", "Count of activities with actual dates in the future, or forecast dates in the past",
        f"{len(invalid)}", f"= {thresholds['invalid_dates_count_max']}",
        _status(len(invalid), thresholds["invalid_dates_count_max"]),
        invalid["task_code"].tolist(),
    ))

    # ---- 10. Resources ------------------------------------------------------
    if "resource_assigned" in detail.columns:
        missing_res = detail[~detail["resource_assigned"]]
        pct_res = 100 * len(missing_res) / total_detail
        metrics.append(DcmaMetric(
            10, "Resources", "% of activities with no resource assigned",
            f"{pct_res:.1f}%", f"≤ {thresholds['resources_missing_pct_max']}%",
            _status(pct_res, thresholds["resources_missing_pct_max"]),
            missing_res["task_code"].tolist(),
        ))
    else:
        metrics.append(DcmaMetric(
            10, "Resources", "% of activities with no resource assigned",
            "N/A", f"≤ {thresholds['resources_missing_pct_max']}%", "grey",
            note="RSRC/TASKRSRC tables not present in this XER export.",
        ))

    # ---- 11. Missed Activities (vs baseline) -------------------------------
    if baseline_tasks is not None and not baseline_tasks.empty:
        merged = detail.merge(
            baseline_tasks[["task_code", "finish_planned"]], on="task_code", how="left", suffixes=("", "_base")
        )
        should_be_done = merged[(merged["finish_planned_base"] < data_date) & merged["finish_planned_base"].notna()]
        missed = should_be_done[should_be_done["status"] != "Complete"]
        pct_missed = 100 * len(missed) / max(len(should_be_done), 1)
        metrics.append(DcmaMetric(
            11, "Missed Activities", "% of activities baselined to finish by the data date that have not completed",
            f"{pct_missed:.1f}%", f"≤ {thresholds['missed_activities_pct_max']}%",
            _status(pct_missed, thresholds["missed_activities_pct_max"]),
            missed["task_code"].tolist(),
        ))
    else:
        metrics.append(DcmaMetric(
            11, "Missed Activities", "% of activities baselined to finish by the data date that have not completed",
            "N/A", f"≤ {thresholds['missed_activities_pct_max']}%", "grey",
            note="Load a baseline XER to enable this check.",
        ))

    # ---- 12. Critical Path Test ---------------------------------------------
    critical = detail[detail["is_critical"]]
    connected = len(critical) > 0 and (critical["task_id"].isin(has_pred).sum() > 0 or len(critical) == 1)
    metrics.append(DcmaMetric(
        12, "Critical Path Test", "A continuous, logically-linked critical path exists through to programme completion",
        "Traceable" if connected else "Not found", "A continuous critical path should exist",
        "green" if connected else "red",
        [] if connected else critical["task_code"].tolist(),
        note="Simplified connectivity check (a full DCMA CP test extends the longest-lead "
             "activity and confirms the finish milestone slips by the same amount).",
    ))

    # ---- 13. Critical Path Length Index (CPLI) -------------------------------
    if not critical.empty and critical["total_float_days"].abs().sum() >= 0:
        cp_length = (critical["finish_early"].max() - detail["start_early"].min()).days if critical["finish_early"].notna().any() else None
        cp_float = critical["total_float_days"].mean()
        if cp_length and cp_length > 0:
            cpli = (cp_length + cp_float) / cp_length
            metrics.append(DcmaMetric(
                13, "Critical Path Length Index (CPLI)", "(Critical path length + critical path float) / critical path length",
                f"{cpli:.2f}", f"≥ {thresholds['cpli_min']}",
                _status(cpli, thresholds["cpli_min"], invert=True),
            ))
        else:
            metrics.append(DcmaMetric(13, "Critical Path Length Index (CPLI)", "(CP length + CP float) / CP length", "N/A", f"≥ {thresholds['cpli_min']}", "grey", note="Insufficient date data on the critical path."))
    else:
        metrics.append(DcmaMetric(13, "Critical Path Length Index (CPLI)", "(CP length + CP float) / CP length", "N/A", f"≥ {thresholds['cpli_min']}", "grey", note="No critical activities identified."))

    # ---- 14. Baseline Execution Index (BEI) ----------------------------------
    if baseline_tasks is not None and not baseline_tasks.empty:
        merged = detail.merge(baseline_tasks[["task_code", "finish_planned"]], on="task_code", how="left", suffixes=("", "_base"))
        should_be_done = merged[(merged["finish_planned_base"] < data_date) & merged["finish_planned_base"].notna()]
        actually_done = should_be_done[should_be_done["status"] == "Complete"]
        bei = len(actually_done) / max(len(should_be_done), 1)
        metrics.append(DcmaMetric(
            14, "Baseline Execution Index (BEI)", "Activities completed ÷ activities baselined to complete by the data date",
            f"{bei:.2f}", f"≥ {thresholds['baseline_execution_index_min']}",
            _status(bei, thresholds["baseline_execution_index_min"], invert=True),
        ))
    else:
        metrics.append(DcmaMetric(14, "Baseline Execution Index (BEI)", "Activities completed ÷ activities baselined to complete by the data date", "N/A", f"≥ {thresholds['baseline_execution_index_min']}", "grey", note="Load a baseline XER to enable this check."))

    return metrics


def summary_counts(metrics: List[DcmaMetric]) -> dict:
    counts = {"green": 0, "amber": 0, "red": 0, "grey": 0}
    for m in metrics:
        counts[m.status] += 1
    return counts
