"""Module 10: IFC Drawing Handover Tracker."""
import pandas as pd
import streamlit as st

from core.data_access import get_live_tasks, require_live_data
from core.dates import fmt_date
from core.modules.ifc_tracker import build_ifc_status
from core.page import bootstrap
from core.state import get_settings
from core.theme import rag_color

bootstrap("Module 10 · IFC Drawing Tracker", "📐")
require_live_data("IFC Drawing Handover Tracker")

st.markdown('<div class="pd-section-title">📐 Module 10 — IFC Drawing Handover Tracker</div>', unsafe_allow_html=True)
st.caption(
    "Flags downstream exposure where an Issued-For-Construction package is late or missing relative "
    "to the construction activities that need it. Tag both the engineering and construction "
    "activities for a package with the same IFC package activity code (⚙️ Settings) to link them."
)

tasks = get_live_tasks()
settings = get_settings()
data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()

status = build_ifc_status(tasks, settings["ifc_warning_days"], data_date)

if status.empty:
    st.info(f"No activities tagged with the '{settings['ifc_package_activity_code_type']}' activity code.", icon="ℹ️")
    st.stop()

for _, row in status.iterrows():
    color = rag_color(row["status"])
    buffer_text = f"{int(row['buffer_days'])} day buffer" if row["buffer_days"] is not None else "No linked construction activity found"
    st.markdown(
        f"""
        <div class="pd-card" style="margin-bottom:0.8rem; border-left:4px solid {color};">
            <div class="pd-card-title">{row['package']}</div>
            <div class="pd-card-value">IFC finish: {fmt_date(row['ifc_finish'])}</div>
            <div class="pd-card-subtitle">Construction start: {fmt_date(row['construction_start'])} · {buffer_text}
            {" · ⚠️ " + str(row['exposed_activities']) + " downstream activities exposed" if row['exposed_activities'] else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(max((row["buffer_days"] or 0) / max(settings["ifc_warning_days"] * 2, 1), 0), 1.0))

status_display = status.copy()
for c in ["ifc_finish", "construction_start"]:
    status_display[c] = status_display[c].apply(fmt_date)
st.dataframe(status_display, use_container_width=True, hide_index=True)
st.download_button("⬇️ Export IFC tracker (CSV)", status.to_csv(index=False), file_name="ifc_tracker.csv", mime="text/csv")
