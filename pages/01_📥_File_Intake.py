"""Module 0: File Intake.

Drag-and-drop panel with two labelled XER drop zones (current live XER,
last accepted baseline XER). The baseline is cached locally so only the
live XER needs re-uploading each reporting cycle. Parses PROJECT, PROJWBS,
TASK, TASKPRED (plus activity-code tables when present) and flags
malformed/missing data rather than failing silently.
"""
import datetime as dt

import pandas as pd
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_tasks, invalidate_settings_dependent_caches
from core.history import record_cycle_snapshot
from core.page import bootstrap
from core.sample_data import generate_demo_xer_bytes
from core.state import cache_baseline, clear_cached_baseline, get_baseline, get_live, get_settings, set_live
from core.xer_parser import get_calendar_ids, get_calendar_names, parse_xer

bootstrap("Module 0 · File Intake", "📥")

st.markdown('<div class="pd-section-title">Module 0 — File Intake</div>', unsafe_allow_html=True)
st.caption(
    "Drop the current live XER on the left every cycle. The last accepted baseline (right) "
    "is cached locally once loaded, so it doesn't need re-uploading."
)

col_live, col_base = st.columns(2)

# ------------------------------------------------------------------ LIVE
with col_live:
    st.markdown("#### 🟢 Current Live XER")
    live_file = st.file_uploader("Drop the live .xer here", type=["xer"], key="live_upload")
    if live_file is not None:
        raw = live_file.read()
        result = parse_xer(raw, live_file.name)
        set_live(result)

    live = get_live()
    if live is not None:
        if live.ok:
            st.success(f"Loaded **{live.source_filename}** ✅", icon="✅")
        else:
            st.error(f"Problems parsing **{live.source_filename}**", icon="🚫")
        for e in live.errors:
            st.error(e, icon="🚫")
        for w in live.warnings:
            st.warning(w, icon="⚠️")
        with st.expander("Tables found"):
            for t in ["PROJECT", "PROJWBS", "TASK", "TASKPRED"]:
                n = len(live.table(t))
                st.write(f"{'✅' if t in live.tables else '❌'} `{t}` — {n} row(s)")
    else:
        st.info("No live XER loaded yet.")

# --------------------------------------------------------------- BASELINE
with col_base:
    st.markdown("#### 🔵 Last Accepted Baseline XER")
    base_file = st.file_uploader("Drop the baseline .xer here (only needed once)", type=["xer"], key="baseline_upload")
    if base_file is not None:
        raw = base_file.read()
        result = parse_xer(raw, base_file.name)
        cache_baseline(result)

    baseline = get_baseline()
    if baseline is not None:
        if baseline.ok:
            st.success(f"Cached **{baseline.source_filename}** ✅ (loaded from local cache)", icon="✅")
        else:
            st.error(f"Problems parsing **{baseline.source_filename}**", icon="🚫")
        for e in baseline.errors:
            st.error(e, icon="🚫")
        for w in baseline.warnings:
            st.warning(w, icon="⚠️")
        with st.expander("Tables found"):
            for t in ["PROJECT", "PROJWBS", "TASK", "TASKPRED"]:
                n = len(baseline.table(t))
                st.write(f"{'✅' if t in baseline.tables else '❌'} `{t}` — {n} row(s)")
        if st.button("🗑️ Clear cached baseline"):
            clear_cached_baseline()
            st.rerun()
    else:
        st.info("No baseline cached yet.")

st.divider()

# --------------------------------------------------------- CALENDAR CHECK
if get_live() is not None and get_baseline() is not None:
    live_ids = set(get_calendar_ids(get_live()))
    base_ids = set(get_calendar_ids(get_baseline()))
    live_names = get_calendar_names(get_live())
    base_names = get_calendar_names(get_baseline())
    live_set = {live_names.get(i, i) for i in live_ids} if live_names else live_ids
    base_set = {base_names.get(i, i) for i in base_ids} if base_names else base_ids
    if live_set and base_set:
        if live_set == base_set:
            st.success(f"Calendars match between live and baseline: {', '.join(sorted(map(str, live_set)))}", icon="🗓️")
        else:
            st.warning(
                f"⚠️ Calendar mismatch — live uses {sorted(map(str, live_set))}, "
                f"baseline uses {sorted(map(str, base_set))}. Duration/date comparisons "
                "between the two programmes may not be like-for-like.",
                icon="⚠️",
            )

if get_live() is not None and get_live().ok and get_baseline() is not None and get_baseline().ok:
    invalidate_settings_dependent_caches()
    live_tasks = get_live_tasks()
    base_tasks = get_baseline_tasks()
    if live_tasks is not None and not live_tasks.empty:
        data_date_actual = live_tasks["start_actual"].dropna().max() if live_tasks["start_actual"].notna().any() else pd.Timestamp.today()
        record_cycle_snapshot(live_tasks, base_tasks, get_settings(), data_date_actual, get_live().source_filename or "live.xer")

st.divider()
st.markdown("#### 🧪 Try it with demo data")
st.caption(
    "No XER handy right now? Load a synthetic demo programme (clearly not one of Jason's real "
    "projects) to see every module working end-to-end."
)
dcol1, dcol2 = st.columns(2)
with dcol1:
    if st.button("Load demo LIVE programme", use_container_width=True):
        raw = generate_demo_xer_bytes("live", data_date=dt.datetime.now())
        set_live(parse_xer(raw, "DEMO_live.xer"))
        st.rerun()
with dcol2:
    if st.button("Load demo BASELINE programme", use_container_width=True):
        raw = generate_demo_xer_bytes("baseline")
        cache_baseline(parse_xer(raw, "DEMO_baseline.xer"))
        st.rerun()
