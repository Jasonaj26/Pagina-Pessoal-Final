"""Synthetic demo XER generator.

Jason's real XER exports are the actual input to this dashboard - this
module exists purely so the dashboard has something realistic to load on
first run (a "Load Demo Programme" button in Module 0) and so we can
smoke-test every module end-to-end. It is clearly labelled as demo data
everywhere it is offered, and is never presented as one of Jason's real
programmes.
"""
from __future__ import annotations

import datetime as dt
import random
from typing import Dict

import pandas as pd

HOURS_PER_DAY = 8

DISCIPLINES = [
    "Engineering",
    "Procurement",
    "Civils",
    "Construction/Installation",
    "Commissioning",
]

DEMO_BASE_DATE = dt.datetime(2026, 1, 5, 8, 0)


def _xer_dt(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


def _xer_date(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d")


def generate_demo_tables(variant: str = "live", data_date: dt.datetime | None = None) -> Dict[str, pd.DataFrame]:
    """variant: 'live' (in-progress, some slippage) or 'baseline' (accepted, no actuals)."""
    random.seed(42)
    data_date = data_date or (dt.datetime(2026, 6, 15) if variant == "live" else dt.datetime(2026, 1, 1))

    project = pd.DataFrame([{
        "proj_id": "100",
        "proj_short_name": "DEMO-BASELINE" if variant == "baseline" else "DEMO-LIVE-JUN26",
        "proj_name": "Demo Infrastructure Programme",
        "plan_start_date": _xer_dt(DEMO_BASE_DATE),
        "plan_end_date": _xer_dt(DEMO_BASE_DATE + dt.timedelta(days=420)),
        "last_recalc_date": _xer_dt(data_date),
    }])

    calendar = pd.DataFrame([{"clndr_id": "1", "clndr_name": "5 Day Week"}])

    wbs_rows = []
    for i, disc in enumerate(DISCIPLINES, start=1):
        wbs_rows.append({"wbs_id": str(1000 + i), "proj_id": "100", "wbs_name": disc, "wbs_short_name": disc[:4].upper(), "parent_wbs_id": ""})
    projwbs = pd.DataFrame(wbs_rows)

    actvtype_defs = [
        ("1", "Discipline"), ("2", "KeyDate"), ("3", "Interface"),
        ("4", "Constraint"), ("5", "IFCPackage"), ("6", "ProcPackage"), ("7", "CENumber"),
    ]
    actvtype = pd.DataFrame([{"actv_code_type_id": tid, "actv_code_type": name} for tid, name in actvtype_defs])

    actvcode_rows = []
    code_id_counter = 1
    code_ids: Dict[str, Dict[str, str]] = {t: {} for _, t in actvtype_defs}
    for disc in DISCIPLINES:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "1", "short_name": disc})
        code_ids["Discipline"][disc] = cid
        code_id_counter += 1
    for kd in ["Planning Consent", "Substation Energisation", "Site Handover"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "2", "short_name": kd})
        code_ids["KeyDate"][kd] = cid
        code_id_counter += 1
    for iface in ["Grid Interface", "Client Interface", "Third Party Interface"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "3", "short_name": iface})
        code_ids["Interface"][iface] = cid
        code_id_counter += 1
    for cons in ["Land Access", "Permit", "Client Approval"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "4", "short_name": cons})
        code_ids["Constraint"][cons] = cid
        code_id_counter += 1
    for pkg in ["Structural Steel Package", "MEP Package", "Foundations Package"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "5", "short_name": pkg})
        code_ids["IFCPackage"][pkg] = cid
        code_id_counter += 1
    for pkg in ["Transformer", "Switchgear", "Control Panels"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "6", "short_name": pkg})
        code_ids["ProcPackage"][pkg] = cid
        code_id_counter += 1
    for ce in ["CE-014", "CE-021"]:
        cid = f"AC{code_id_counter}"
        actvcode_rows.append({"actv_code_id": cid, "actv_code_type_id": "7", "short_name": ce})
        code_ids["CENumber"][ce] = cid
        code_id_counter += 1
    actvcode = pd.DataFrame(actvcode_rows)

    tasks = []
    preds = []
    taskactv_rows = []
    task_id_counter = 2000
    prev_task_by_disc: Dict[str, str] = {}
    cursor = DEMO_BASE_DATE

    for d_idx, disc in enumerate(DISCIPLINES):
        n_tasks = 14
        disc_start = DEMO_BASE_DATE + dt.timedelta(days=d_idx * 45)
        cursor = disc_start
        for i in range(n_tasks):
            task_id = str(task_id_counter)
            task_id_counter += 1
            dur_days = random.randint(4, 18)
            planned_start = cursor
            planned_finish = cursor + dt.timedelta(days=dur_days)
            cursor = planned_finish + dt.timedelta(days=random.choice([0, 0, 1]))

            is_milestone = False
            task_type = "TT_Task"
            total_float_days = 0
            if variant == "live":
                total_float_days = random.choice([0, 0, 0, 2, 5, 10, 25, 50, -3 if i == 3 and d_idx == 3 else 0])
            else:
                total_float_days = random.choice([0, 0, 3, 8, 15])

            completed = variant == "live" and planned_finish < data_date - dt.timedelta(days=20)
            in_progress = variant == "live" and planned_start < data_date <= planned_finish + dt.timedelta(days=15)

            act_start = ""
            act_finish = ""
            pct = 0
            status = "TK_NotStart"
            slip_days = 0
            if completed:
                status = "TK_Complete"
                pct = 100
                slip = random.choice([0, 0, 2, 4])
                act_start = _xer_dt(planned_start)
                act_finish = _xer_dt(planned_finish + dt.timedelta(days=slip))
                slip_days = slip
            elif in_progress:
                status = "TK_Active"
                pct = random.randint(10, 85)
                act_start = _xer_dt(planned_start)

            row = {
                "task_id": task_id,
                "proj_id": "100",
                "wbs_id": str(1001 + d_idx),
                "task_code": f"{disc[:3].upper()}-{1000 + i}",
                "task_name": f"{disc} activity {i + 1}",
                "task_type": task_type,
                "status_code": status,
                "phys_complete_pct": pct,
                "target_start_date": _xer_dt(planned_start),
                "target_end_date": _xer_dt(planned_finish + dt.timedelta(days=slip_days if variant == "live" else 0)),
                "act_start_date": act_start,
                "act_end_date": act_finish,
                "early_start_date": _xer_dt(planned_start),
                "early_end_date": _xer_dt(planned_finish + dt.timedelta(days=slip_days if variant == "live" else 0)),
                "late_start_date": _xer_dt(planned_start + dt.timedelta(days=total_float_days)),
                "late_end_date": _xer_dt(planned_finish + dt.timedelta(days=total_float_days)),
                "target_drtn_hr_cnt": dur_days * HOURS_PER_DAY,
                "remain_drtn_hr_cnt": 0 if completed else dur_days * HOURS_PER_DAY,
                "total_float_hr_cnt": total_float_days * HOURS_PER_DAY,
                "free_float_hr_cnt": max(total_float_days - 2, 0) * HOURS_PER_DAY,
                "driving_path_flag": "Y" if total_float_days <= 0 else "N",
                "cstr_type": "CS_MSO" if (i == 0 and d_idx in (2, 3)) else "",
                "cstr_date": _xer_dt(planned_start) if (i == 0 and d_idx in (2, 3)) else "",
                "clndr_id": "1",
            }
            tasks.append(row)
            taskactv_rows.append({"task_id": task_id, "actv_code_type_id": "1", "actv_code_id": code_ids["Discipline"][disc]})

            if prev_task_by_disc.get(disc):
                preds.append({
                    "task_pred_id": f"P{task_id}",
                    "task_id": task_id,
                    "pred_task_id": prev_task_by_disc[disc],
                    "proj_id": "100",
                    "pred_type": "PR_FS",
                    "lag_hr_cnt": 0,
                })
            prev_task_by_disc[disc] = task_id

        # cross-discipline handoff (engineering -> procurement -> civils -> construction -> commissioning)
        if d_idx > 0:
            prev_disc = DISCIPLINES[d_idx - 1]
            first_task_this_disc = tasks[-n_tasks]["task_id"]
            last_task_prev_disc = prev_task_by_disc.get(prev_disc)
            if last_task_prev_disc:
                preds.append({
                    "task_pred_id": f"X{first_task_this_disc}",
                    "task_id": first_task_this_disc,
                    "pred_task_id": last_task_prev_disc,
                    "proj_id": "100",
                    "pred_type": "PR_FS",
                    "lag_hr_cnt": 0,
                })

    # ---- Extra activity-code tagging so the demo exercises every generic
    # tracker module (Interface/Constraint, IFC, Procurement) end-to-end,
    # using the same shared-code-across-disciplines linkage pattern real
    # usage would follow. Indices below are positions within `tasks`,
    # which was built discipline-by-discipline (14 each, in DISCIPLINES order).
    eng_start, proc_start, civ_start, con_start, comm_start = (0, 14, 28, 42, 56)

    def _tag(idx: int, type_id: str, code_id: str) -> None:
        taskactv_rows.append({"task_id": tasks[idx]["task_id"], "actv_code_type_id": type_id, "actv_code_id": code_id})

    # IFC package: engineering issuance -> construction need
    for idx in (eng_start + 2, eng_start + 3):
        _tag(idx, "5", code_ids["IFCPackage"]["Structural Steel Package"])
    for idx in (con_start + 2, con_start + 3):
        _tag(idx, "5", code_ids["IFCPackage"]["Structural Steel Package"])

    # Procurement package: procurement order/delivery -> construction need
    for idx in (proc_start + 2, proc_start + 3):
        _tag(idx, "6", code_ids["ProcPackage"]["Transformer"])
    for idx in (con_start + 5, con_start + 6):
        _tag(idx, "6", code_ids["ProcPackage"]["Transformer"])

    # Interfaces and constraints scattered across a few activities
    _tag(eng_start + 5, "3", code_ids["Interface"]["Grid Interface"])
    _tag(civ_start + 4, "3", code_ids["Interface"]["Client Interface"])
    _tag(comm_start + 1, "3", code_ids["Interface"]["Third Party Interface"])
    _tag(civ_start + 1, "4", code_ids["Constraint"]["Land Access"])
    _tag(eng_start + 1, "4", code_ids["Constraint"]["Permit"])

    # One CE genuinely reflected by a logic change in the live programme (CE-021);
    # CE-014 is deliberately left unlinked so Module 13 has something to flag.
    if variant == "live":
        _tag(con_start + 7, "7", code_ids["CENumber"]["CE-021"])

    # Key date milestones
    key_date_targets = {
        "Planning Consent": (DEMO_BASE_DATE + dt.timedelta(days=40), "Engineering"),
        "Site Handover": (DEMO_BASE_DATE + dt.timedelta(days=180), "Civils"),
        "Substation Energisation": (DEMO_BASE_DATE + dt.timedelta(days=380), "Commissioning"),
    }
    for kd_name, (kd_date, disc) in key_date_targets.items():
        task_id = str(task_id_counter)
        task_id_counter += 1
        slip = random.choice([0, 3, 9]) if variant == "live" else 0
        actual_date = kd_date + dt.timedelta(days=slip)
        tasks.append({
            "task_id": task_id,
            "proj_id": "100",
            "wbs_id": "1001",
            "task_code": f"KD-{kd_name[:3].upper()}",
            "task_name": kd_name,
            "task_type": "TT_FinMile",
            "status_code": "TK_NotStart",
            "phys_complete_pct": 0,
            "target_start_date": _xer_dt(kd_date),
            "target_end_date": _xer_dt(actual_date),
            "act_start_date": "",
            "act_end_date": "",
            "early_start_date": _xer_dt(actual_date),
            "early_end_date": _xer_dt(actual_date),
            "late_start_date": _xer_dt(actual_date),
            "late_end_date": _xer_dt(actual_date),
            "target_drtn_hr_cnt": 0,
            "remain_drtn_hr_cnt": 0,
            "total_float_hr_cnt": 0,
            "free_float_hr_cnt": 0,
            "driving_path_flag": "Y",
            "cstr_type": "",
            "cstr_date": "",
            "clndr_id": "1",
        })
        taskactv_rows.append({"task_id": task_id, "actv_code_type_id": "2", "actv_code_id": code_ids["KeyDate"][kd_name]})

    task_df = pd.DataFrame(tasks)
    pred_df = pd.DataFrame(preds)
    taskactv_df = pd.DataFrame(taskactv_rows)

    return {
        "PROJECT": project,
        "CALENDAR": calendar,
        "PROJWBS": projwbs,
        "ACTVTYPE": actvtype,
        "ACTVCODE": actvcode,
        "TASK": task_df,
        "TASKPRED": pred_df,
        "TASKACTV": taskactv_df,
    }


def tables_to_xer_bytes(tables: Dict[str, pd.DataFrame]) -> bytes:
    lines = ["%ERMHDR\t20.12\t" + _xer_date(dt.datetime.now()) + "\tProject\tdemo\tdemo\tDemo\tGBP"]
    for name, df in tables.items():
        lines.append(f"%T\t{name}")
        lines.append("%F\t" + "\t".join(df.columns))
        for _, row in df.iterrows():
            lines.append("%R\t" + "\t".join("" if pd.isna(v) else str(v) for v in row.values))
    lines.append("%E")
    return ("\n".join(lines)).encode("utf-8")


def generate_demo_xer_bytes(variant: str = "live", data_date: dt.datetime | None = None) -> bytes:
    return tables_to_xer_bytes(generate_demo_tables(variant=variant, data_date=data_date))
