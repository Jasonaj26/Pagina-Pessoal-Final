"""Module 3: AI Narrative Layer.

Entirely rule-based, plain-English schedule health observations built
from the outputs of the other modules. No external API calls, no LLM
dependency - everything here runs locally from DataFrames already in
memory.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd


def narrative_from_dcma(metrics) -> List[str]:
    sentences = []
    reds = [m for m in metrics if m.status == "red"]
    ambers = [m for m in metrics if m.status == "amber"]
    if not reds and not ambers:
        sentences.append("✅ The schedule passes all scored DCMA 14-point checks - no red or amber flags.")
    if reds:
        names = ", ".join(m.name for m in reds)
        sentences.append(f"🔴 {len(reds)} DCMA check(s) are failing outright: {names}. These are the highest-priority schedule quality issues to correct.")
    if ambers:
        names = ", ".join(m.name for m in ambers)
        sentences.append(f"🟠 {len(ambers)} DCMA check(s) are borderline: {names}. Worth tidying up before they become red.")

    neg_float = next((m for m in metrics if m.name == "Negative Float"), None)
    if neg_float and neg_float.failing_ids:
        sentences.append(
            f"⚠️ {len(neg_float.failing_ids)} activities are showing negative float, meaning the schedule "
            "logic currently predicts missing a required date - this needs mitigation, acceleration, or "
            "a scope/logic review."
        )
    logic = next((m for m in metrics if m.name == "Logic"), None)
    if logic and logic.failing_ids:
        sentences.append(
            f"🔗 {len(logic.failing_ids)} incomplete activities are missing a predecessor and/or successor - "
            "float and dates calculated for these (and anything downstream of them) may not be reliable."
        )
    return sentences


def narrative_from_monte_carlo(mc_result, deterministic_finish: Optional[pd.Timestamp] = None) -> List[str]:
    sentences = []
    if mc_result is None:
        return sentences
    p50 = mc_result.percentiles.get(50)
    p80 = mc_result.percentiles.get(80)
    p90 = mc_result.percentiles.get(90)
    if p50 is not None:
        sentences.append(f"🎲 The Monte Carlo simulation ({mc_result.iterations:,} iterations) puts P50 completion at {p50.strftime('%d/%m/%Y')}.")
    if p50 is not None and p90 is not None:
        spread = (p90 - p50).days
        if spread > 60:
            sentences.append(f"📈 There is wide schedule risk exposure: P90 sits {spread} calendar days beyond P50, suggesting significant uncertainty still to manage down.")
        elif spread > 20:
            sentences.append(f"📈 P90 sits {spread} calendar days beyond P50 - a moderate but manageable spread of schedule risk.")
        else:
            sentences.append(f"📈 The P50-P90 spread is tight ({spread} days), indicating the programme's completion date is relatively well-converged.")
    if deterministic_finish is not None and p50 is not None:
        delta = (p50 - deterministic_finish).days
        if delta > 10:
            sentences.append(f"⏱️ Monte Carlo P50 is running {delta} days later than the deterministic CPM finish date - discipline uncertainty bands are pulling the risk-adjusted date out further than the raw schedule shows.")
    if mc_result.warnings:
        sentences.extend(f"ℹ️ {w}" for w in mc_result.warnings)
    return sentences


def narrative_from_spi(spi_by_discipline: pd.DataFrame) -> List[str]:
    sentences = []
    if spi_by_discipline is None or spi_by_discipline.empty:
        return sentences
    worst = spi_by_discipline.sort_values("spi_duration").iloc[0]
    best = spi_by_discipline.sort_values("spi_duration", ascending=False).iloc[0]
    if worst["spi_duration"] < 0.85:
        sentences.append(
            f"📉 {worst['discipline']} is the weakest-performing discipline on duration-weighted SPI "
            f"({worst['spi_duration']:.2f}), with {int(worst['sv_count'])} activities behind baseline "
            f"totalling {int(worst['sv_days'])} working days of slippage."
        )
    if best["spi_duration"] >= 1.0:
        sentences.append(f"✅ {best['discipline']} is on or ahead of baseline (SPI {best['spi_duration']:.2f}).")
    lagging = spi_by_discipline[spi_by_discipline["spi_duration"] < 0.95]
    if len(lagging) >= 2:
        names = ", ".join(lagging["discipline"].tolist())
        sentences.append(f"⚠️ Multiple disciplines are trending behind baseline: {names}.")
    return sentences


def narrative_from_key_dates(key_date_status: pd.DataFrame, slip_flags: pd.DataFrame) -> List[str]:
    sentences = []
    if key_date_status is None or key_date_status.empty:
        return sentences
    red = key_date_status[key_date_status["status"] == "red"]
    amber = key_date_status[key_date_status["status"] == "amber"]
    if not red.empty:
        names = ", ".join(red["key_date_name"].tolist())
        sentences.append(f"🔴 Key date(s) at red status against baseline: {names}.")
    if not amber.empty:
        names = ", ".join(amber["key_date_name"].tolist())
        sentences.append(f"🟠 Key date(s) trending amber against baseline: {names}.")
    if slip_flags is not None and not slip_flags.empty:
        repeat = slip_flags[slip_flags["consecutive_slips"] >= 2]
        for _, row in repeat.iterrows():
            sentences.append(f"📅 {row['key_date_name']} has slipped for {int(row['consecutive_slips'])} consecutive reporting cycles - this is a trend, not a one-off.")
    if red.empty and amber.empty:
        sentences.append("✅ All key dates are currently tracking at or ahead of baseline.")
    return sentences


def build_full_narrative(dcma_metrics=None, mc_result=None, deterministic_finish=None, spi_by_discipline=None, key_date_status=None, slip_flags=None) -> dict:
    return {
        "Schedule Quality (DCMA)": narrative_from_dcma(dcma_metrics) if dcma_metrics else ["Run the DCMA 14-Point Assessment to see schedule-quality observations here."],
        "Schedule Risk (Monte Carlo)": narrative_from_monte_carlo(mc_result, deterministic_finish) if mc_result else ["Run the Monte Carlo QSRA to see schedule-risk observations here."],
        "Performance (SPI)": narrative_from_spi(spi_by_discipline) if spi_by_discipline is not None else ["Load a baseline and visit SPI by Discipline to see performance observations here."],
        "Key Dates": narrative_from_key_dates(key_date_status, slip_flags) if key_date_status is not None else ["Visit Key Date Tracking to see key-date observations here."],
    }
