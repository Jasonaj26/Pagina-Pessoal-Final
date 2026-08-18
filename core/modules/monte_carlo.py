"""Module 1: Monte Carlo QSRA.

PERT-beta distributed durations sampled per activity (uncertainty band by
discipline, all user-editable), propagated across the real network logic
in TASK/TASKPRED via a vectorised forward-pass (CPM-style) simulation, for
a minimum of 10,000 iterations.

This is a simplified schedule-risk engine (single calendar, FS/SS/FF/SF
relationships honoured, no resource levelling) - appropriate for a
programme-level QSRA read, not a replacement for a dedicated risk tool.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class MonteCarloResult:
    iterations: int
    finish_offsets_days: np.ndarray  # shape (iterations,) - days from data_date
    data_date: pd.Timestamp
    task_ids_simulated: List[str]
    duration_samples: np.ndarray  # shape (iterations, n_tasks_simulated)
    task_index: Dict[str, int]
    percentiles: Dict[int, pd.Timestamp]
    warnings: List[str]
    baseline_deterministic_offset: float


def _pert_beta_samples(low: np.ndarray, mode: np.ndarray, high: np.ndarray, n_iter: int, rng: np.random.Generator) -> np.ndarray:
    """Vectorised PERT-via-Beta sampling for many activities at once.

    low/mode/high shape: (n_tasks,). Returns shape (n_iter, n_tasks).
    """
    span = np.maximum(high - low, 1e-9)
    alpha = 1 + 4 * (mode - low) / span
    beta = 1 + 4 * (high - mode) / span
    alpha = np.clip(alpha, 0.1, None)
    beta = np.clip(beta, 0.1, None)
    raw = rng.beta(alpha, beta, size=(n_iter, len(low)))
    return low + raw * span


def _topo_order(task_ids: List[str], preds_by_task: Dict[str, list]) -> tuple[List[str], List[str]]:
    """Kahn's algorithm. Returns (order, warnings). Breaks cycles if found."""
    warnings: List[str] = []
    in_degree = {t: len(preds_by_task.get(t, [])) for t in task_ids}
    succ_map: Dict[str, list] = {t: [] for t in task_ids}
    for t, preds in preds_by_task.items():
        for p in preds:
            pred_id = p["pred_task_id"]
            if pred_id in succ_map:
                succ_map[pred_id].append(t)

    queue = [t for t in task_ids if in_degree[t] == 0]
    order: List[str] = []
    remaining_in_degree = dict(in_degree)
    while queue:
        node = queue.pop()
        order.append(node)
        for s in succ_map.get(node, []):
            remaining_in_degree[s] -= 1
            if remaining_in_degree[s] == 0:
                queue.append(s)

    if len(order) < len(task_ids):
        missing = [t for t in task_ids if t not in order]
        warnings.append(
            f"{len(missing)} activities are part of a logic loop (circular predecessor "
            "relationships) and were appended in arbitrary order for the simulation - "
            "check TASKPRED for closed loops."
        )
        order.extend(missing)
    return order, warnings


def run_monte_carlo(
    tasks: pd.DataFrame,
    relationships: pd.DataFrame,
    discipline_bands_pct: Dict[str, float],
    iterations: int = 10000,
    confidence_levels: Optional[List[int]] = None,
    data_date: Optional[pd.Timestamp] = None,
    seed: int = 12345,
) -> MonteCarloResult:
    confidence_levels = confidence_levels or [50, 80, 90]
    warnings: List[str] = []
    rng = np.random.default_rng(seed)

    if data_date is None:
        candidates = tasks["start_actual"].dropna().tolist() + [pd.Timestamp.today()]
        data_date = max(candidates) if candidates else pd.Timestamp.today()

    work = tasks[tasks["task_type"] != "TT_WBS"].copy()
    work = work[~work["task_code"].isna()]

    task_ids = work["task_id"].tolist()
    idx_of = {t: i for i, t in enumerate(task_ids)}
    n = len(task_ids)

    is_complete = (work["status"] == "Complete").to_numpy()
    is_started = work["start_actual"].notna().to_numpy() & ~is_complete
    remaining_days = work["duration_remaining_days"].fillna(0).clip(lower=0).to_numpy()
    planned_days = work["duration_planned_days"].fillna(0).clip(lower=0).to_numpy()
    disciplines = work["discipline"].fillna("Other").to_numpy()

    band_pct = np.array([discipline_bands_pct.get(d, discipline_bands_pct.get("Other", 15)) for d in disciplines]) / 100.0

    base_duration = np.where(remaining_days > 0, remaining_days, planned_days)
    low = base_duration * (1 - band_pct)
    mode = base_duration
    high = base_duration * (1 + band_pct)
    low = np.clip(low, 0, None)
    high = np.maximum(high, low + 1e-6)

    simulate_mask = (~is_complete) & (base_duration > 0)
    n_sim = int(simulate_mask.sum())

    duration_samples_sub = _pert_beta_samples(low[simulate_mask], mode[simulate_mask], high[simulate_mask], iterations, rng) if n_sim > 0 else np.zeros((iterations, 0))

    duration_matrix = np.tile(base_duration, (iterations, 1)).astype(float)
    if n_sim > 0:
        duration_matrix[:, simulate_mask] = duration_samples_sub

    # anchor offset (days from data_date) for completed / not-yet-touched baseline
    finish_actual_days = (work["finish_actual"] - data_date).dt.days
    anchor_offset = finish_actual_days.fillna(0).clip(lower=0).to_numpy().astype(float)

    preds_by_task: Dict[str, list] = {}
    for _, row in relationships.iterrows():
        if row["task_id"] not in idx_of or row["pred_task_id"] not in idx_of:
            continue
        preds_by_task.setdefault(row["task_id"], []).append(
            {"pred_task_id": row["pred_task_id"], "type": row["type"], "lag_days": row["lag_days"]}
        )

    order, topo_warnings = _topo_order(task_ids, preds_by_task)
    warnings.extend(topo_warnings)

    early_start = np.zeros((iterations, n))
    early_finish = np.zeros((iterations, n))

    for task_id in order:
        i = idx_of[task_id]
        if is_complete[i]:
            early_start[:, i] = anchor_offset[i]
            early_finish[:, i] = anchor_offset[i]
            continue

        candidates = [np.zeros(iterations)] if is_started[i] else []
        for p in preds_by_task.get(task_id, []):
            pj = idx_of.get(p["pred_task_id"])
            if pj is None:
                continue
            lag = float(p["lag_days"] or 0)
            ptype = (p["type"] or "PR_FS").upper()
            if ptype == "PR_FS":
                candidates.append(early_finish[:, pj] + lag)
            elif ptype == "PR_SS":
                candidates.append(early_start[:, pj] + lag)
            elif ptype == "PR_FF":
                candidates.append(early_finish[:, pj] + lag - duration_matrix[:, i])
            elif ptype == "PR_SF":
                candidates.append(early_start[:, pj] + lag - duration_matrix[:, i])
            else:
                candidates.append(early_finish[:, pj] + lag)

        if candidates:
            es = np.maximum.reduce(candidates)
        else:
            es = np.zeros(iterations)
        es = np.maximum(es, 0)
        early_start[:, i] = es
        early_finish[:, i] = es + duration_matrix[:, i]

    finish_offsets = early_finish.max(axis=1) if n > 0 else np.zeros(iterations)

    percentiles: Dict[int, pd.Timestamp] = {}
    for p in confidence_levels:
        offset_days = float(np.percentile(finish_offsets, p))
        percentiles[p] = data_date + pd.Timedelta(days=offset_days)

    baseline_deterministic_offset = float(np.max(anchor_offset + np.where(is_complete, 0, base_duration))) if n > 0 else 0.0

    return MonteCarloResult(
        iterations=iterations,
        finish_offsets_days=finish_offsets,
        data_date=data_date,
        task_ids_simulated=[t for t, m in zip(task_ids, simulate_mask) if m],
        duration_samples=duration_samples_sub,
        task_index={t: i for i, t in enumerate([t for t, m in zip(task_ids, simulate_mask) if m])},
        percentiles=percentiles,
        warnings=warnings,
        baseline_deterministic_offset=baseline_deterministic_offset,
    )


def tornado_drivers(result: MonteCarloResult, tasks: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """Correlation between each simulated activity's duration and total project
    completion, as a schedule-risk 'sensitivity' tornado."""
    if result.duration_samples.shape[1] == 0:
        return pd.DataFrame(columns=["task_id", "task_code", "task_name", "discipline", "correlation"])

    total = result.finish_offsets_days
    corr = []
    for task_id, i in result.task_index.items():
        col = result.duration_samples[:, i]
        if np.std(col) < 1e-9 or np.std(total) < 1e-9:
            c = 0.0
        else:
            c = float(np.corrcoef(col, total)[0, 1])
        corr.append((task_id, c))

    corr_df = pd.DataFrame(corr, columns=["task_id", "correlation"])
    meta = tasks[["task_id", "task_code", "task_name", "discipline"]]
    merged = corr_df.merge(meta, on="task_id", how="left")
    merged["abs_corr"] = merged["correlation"].abs()
    merged = merged.sort_values("abs_corr", ascending=False).head(top_n)
    return merged.drop(columns="abs_corr")
