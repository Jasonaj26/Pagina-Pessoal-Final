"""Builds a normalised, analysis-ready activity table from raw XER tables.

Every module downstream (Monte Carlo, DCMA, SPI, Gantt, trackers...) reads
from this single enriched DataFrame rather than touching raw XER columns
directly, so field-name quirks only need to be handled once.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from core.xer_parser import XerParseResult

HOURS_PER_DAY = 8.0

TASK_TYPE_MILESTONES = {"TT_Mile", "TT_FinMile"}

STATUS_MAP = {
    "TK_NotStart": "Not Started",
    "TK_Active": "In Progress",
    "TK_Complete": "Complete",
}


def _col(df: pd.DataFrame, *names: str) -> Optional[str]:
    for n in names:
        if n in df.columns:
            return n
    return None


def _num(series: Optional[pd.Series]) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(series, errors="coerce")


def _date(series: Optional[pd.Series]) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(series, errors="coerce")


def build_activity_code_lookup(result: XerParseResult, code_type_name: str) -> Dict[str, str]:
    """task_id -> code short-name for a named activity code type (e.g. 'Discipline').

    Returns {} gracefully if ACTVTYPE/ACTVCODE/TASKACTV aren't present in this
    export - callers should fall back to keyword classification in that case.
    """
    actv_type = result.table("ACTVTYPE")
    actv_code = result.table("ACTVCODE")
    task_actv = result.table("TASKACTV")
    if actv_type.empty or actv_code.empty or task_actv.empty:
        return {}

    type_name_col = _col(actv_type, "actv_code_type", "actv_code_type_name")
    type_id_col = _col(actv_type, "actv_code_type_id")
    if not type_name_col or not type_id_col:
        return {}

    matching_types = actv_type[actv_type[type_name_col].astype(str).str.strip().str.lower() == code_type_name.strip().lower()]
    if matching_types.empty:
        return {}
    type_ids = set(matching_types[type_id_col].astype(str))

    code_id_col = _col(actv_code, "actv_code_id")
    code_type_id_col = _col(actv_code, "actv_code_type_id")
    code_value_col = _col(actv_code, "short_name", "actv_code_name", "actv_code")
    if not code_id_col or not code_type_id_col or not code_value_col:
        return {}

    codes = actv_code[actv_code[code_type_id_col].astype(str).isin(type_ids)]
    code_value_by_id = dict(zip(codes[code_id_col].astype(str), codes[code_value_col].astype(str)))

    ta_task_col = _col(task_actv, "task_id")
    ta_code_col = _col(task_actv, "actv_code_id")
    ta_type_col = _col(task_actv, "actv_code_type_id")
    if not ta_task_col or not ta_code_col:
        return {}

    relevant = task_actv
    if ta_type_col:
        relevant = task_actv[task_actv[ta_type_col].astype(str).isin(type_ids)]

    lookup: Dict[str, str] = {}
    for _, row in relevant.iterrows():
        code_id = str(row[ta_code_col])
        if code_id in code_value_by_id:
            lookup[str(row[ta_task_col])] = code_value_by_id[code_id]
    return lookup


def classify_discipline(task_code: str, task_name: str, keywords: Dict[str, list]) -> str:
    haystack = f"{task_code} {task_name}".upper()
    for discipline, kws in keywords.items():
        for kw in kws:
            if kw and kw.upper() in haystack:
                return discipline
    return "Other"


def build_enriched_tasks(result: XerParseResult, settings: dict) -> pd.DataFrame:
    task_df = result.table("TASK")
    if task_df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["task_id"] = task_df[_col(task_df, "task_id")].astype(str)
    out["proj_id"] = task_df[_col(task_df, "proj_id")].astype(str) if _col(task_df, "proj_id") else ""
    out["wbs_id"] = task_df[_col(task_df, "wbs_id")].astype(str) if _col(task_df, "wbs_id") else ""
    code_col = _col(task_df, "task_code")
    name_col = _col(task_df, "task_name")
    out["task_code"] = task_df[code_col].astype(str) if code_col else ""
    out["task_name"] = task_df[name_col].astype(str) if name_col else ""

    type_col = _col(task_df, "task_type")
    out["task_type"] = task_df[type_col].astype(str) if type_col else ""
    out["is_milestone"] = out["task_type"].isin(TASK_TYPE_MILESTONES)

    status_col = _col(task_df, "status_code")
    raw_status = task_df[status_col].astype(str) if status_col else pd.Series([""] * len(task_df))
    out["status"] = raw_status.map(STATUS_MAP).fillna(raw_status)

    out["start_planned"] = _date(task_df.get(_col(task_df, "target_start_date")))
    out["finish_planned"] = _date(task_df.get(_col(task_df, "target_end_date")))
    out["start_actual"] = _date(task_df.get(_col(task_df, "act_start_date")))
    out["finish_actual"] = _date(task_df.get(_col(task_df, "act_end_date")))
    out["start_early"] = _date(task_df.get(_col(task_df, "early_start_date")))
    out["finish_early"] = _date(task_df.get(_col(task_df, "early_end_date")))
    out["start_late"] = _date(task_df.get(_col(task_df, "late_start_date")))
    out["finish_late"] = _date(task_df.get(_col(task_df, "late_end_date")))

    out["duration_planned_days"] = _num(task_df.get(_col(task_df, "target_drtn_hr_cnt"))) / HOURS_PER_DAY
    out["duration_remaining_days"] = _num(task_df.get(_col(task_df, "remain_drtn_hr_cnt"))) / HOURS_PER_DAY
    out["total_float_days"] = _num(task_df.get(_col(task_df, "total_float_hr_cnt"))) / HOURS_PER_DAY
    out["free_float_days"] = _num(task_df.get(_col(task_df, "free_float_hr_cnt"))) / HOURS_PER_DAY

    pct_col = _col(task_df, "phys_complete_pct", "drtn_complete_pct")
    out["pct_complete"] = _num(task_df.get(pct_col)) if pct_col else 0.0

    driving_col = _col(task_df, "driving_path_flag")
    out["driving_path"] = (task_df[driving_col].astype(str).str.upper() == "Y") if driving_col else False

    cstr_type_col = _col(task_df, "cstr_type")
    out["constraint_type"] = task_df[cstr_type_col].astype(str) if cstr_type_col else ""
    out["constraint_date"] = _date(task_df.get(_col(task_df, "cstr_date")))

    clndr_col = _col(task_df, "clndr_id")
    out["clndr_id"] = task_df[clndr_col].astype(str) if clndr_col else ""

    # best available start/finish for display/Gantt purposes: actual if set, else early/forecast, else planned
    out["start_display"] = out["start_actual"].combine_first(out["start_early"]).combine_first(out["start_planned"])
    out["finish_display"] = out["finish_actual"].combine_first(out["finish_early"]).combine_first(out["finish_planned"])

    out["is_critical"] = out["total_float_days"].fillna(9999) <= 0

    # ---- Activity-code-driven classification (generic, user-configurable) ----
    discipline_type = settings.get("discipline_activity_code_type", "Discipline")
    discipline_lookup = build_activity_code_lookup(result, discipline_type)
    keywords = settings.get("discipline_keywords", {})

    def _discipline_for_row(row) -> str:
        coded = discipline_lookup.get(row["task_id"])
        if coded:
            return coded
        return classify_discipline(row["task_code"], row["task_name"], keywords)

    out["discipline"] = out.apply(_discipline_for_row, axis=1)

    for settings_key, out_col in (
        ("key_date_activity_code_type", "key_date_code"),
        ("interface_activity_code_type", "interface_code"),
        ("constraint_activity_code_type", "constraint_code"),
        ("ifc_package_activity_code_type", "ifc_package_code"),
        ("procurement_package_activity_code_type", "procurement_package_code"),
        ("ce_link_activity_code_type", "ce_number"),
    ):
        code_type = settings.get(settings_key)
        lookup = build_activity_code_lookup(result, code_type) if code_type else {}
        out[out_col] = out["task_id"].map(lookup).fillna("")

    return out


def build_relationships(result: XerParseResult) -> pd.DataFrame:
    pred_df = result.table("TASKPRED")
    if pred_df.empty:
        return pd.DataFrame(columns=["task_id", "pred_task_id", "type", "lag_days"])
    out = pd.DataFrame()
    out["task_id"] = pred_df[_col(pred_df, "task_id")].astype(str)
    out["pred_task_id"] = pred_df[_col(pred_df, "pred_task_id")].astype(str)
    type_col = _col(pred_df, "pred_type")
    out["type"] = pred_df[type_col].astype(str) if type_col else "PR_FS"
    lag_col = _col(pred_df, "lag_hr_cnt")
    out["lag_days"] = _num(pred_df.get(lag_col)) / HOURS_PER_DAY if lag_col else 0.0
    return out


def build_wbs(result: XerParseResult) -> pd.DataFrame:
    wbs_df = result.table("PROJWBS")
    if wbs_df.empty:
        return pd.DataFrame(columns=["wbs_id", "wbs_name", "parent_wbs_id"])
    out = pd.DataFrame()
    out["wbs_id"] = wbs_df[_col(wbs_df, "wbs_id")].astype(str)
    name_col = _col(wbs_df, "wbs_name", "wbs_short_name")
    out["wbs_name"] = wbs_df[name_col].astype(str) if name_col else ""
    parent_col = _col(wbs_df, "parent_wbs_id")
    out["parent_wbs_id"] = wbs_df[parent_col].astype(str) if parent_col else ""
    return out


def project_info(result: XerParseResult) -> dict:
    proj_df = result.table("PROJECT")
    if proj_df.empty:
        return {}
    row = proj_df.iloc[0]
    name_col = _col(proj_df, "proj_short_name")
    long_name_col = _col(proj_df, "proj_name")
    info = {
        "proj_id": str(row.get(_col(proj_df, "proj_id"), "")),
        "name": str(row.get(name_col, "")) if name_col else "",
        "long_name": str(row.get(long_name_col, "")) if long_name_col else "",
        "plan_start": pd.to_datetime(row.get(_col(proj_df, "plan_start_date")), errors="coerce"),
        "plan_end": pd.to_datetime(row.get(_col(proj_df, "plan_end_date")), errors="coerce"),
        "data_date": pd.to_datetime(row.get(_col(proj_df, "last_recalc_date")), errors="coerce"),
    }
    return info
