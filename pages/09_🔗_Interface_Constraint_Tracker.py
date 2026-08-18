"""Module 8: Generic Interface and Constraint Tracker."""
import pandas as pd
import streamlit as st

from core.data_access import get_live_tasks, require_live_data
from core.dates import fmt_date
from core.modules.interfaces import build_tracker
from core.page import bootstrap
from core.state import get_settings
from core.theme import rag_badge

bootstrap("Module 8 · Interface & Constraint Tracker", "🔗")
require_live_data("Interface & Constraint Tracker")

st.markdown('<div class="pd-section-title">🔗 Module 8 — Interface & Constraint Tracker</div>', unsafe_allow_html=True)
st.caption("Generic tracker driven by activity codes - the code type names are set per project in ⚙️ Settings.")

tasks = get_live_tasks()
settings = get_settings()
data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()

tab1, tab2 = st.tabs(["🔗 Interfaces", "🚧 Constraints"])

with tab1:
    interfaces = build_tracker(tasks, "interface_code", data_date)
    if interfaces.empty:
        st.info(f"No activities tagged with the '{settings['interface_activity_code_type']}' activity code.", icon="ℹ️")
    else:
        interfaces_display = interfaces.copy()
        interfaces_display["finish_display"] = interfaces_display["finish_display"].apply(fmt_date)
        st.dataframe(
            interfaces_display.rename(columns={"interface_code": "Interface", "finish_display": "Finish"}),
            use_container_width=True, hide_index=True,
        )
        st.download_button("⬇️ Export interfaces (CSV)", interfaces.to_csv(index=False), file_name="interface_tracker.csv", mime="text/csv")

with tab2:
    constraints = build_tracker(tasks, "constraint_code", data_date)
    if constraints.empty:
        st.info(f"No activities tagged with the '{settings['constraint_activity_code_type']}' activity code.", icon="ℹ️")
    else:
        constraints_display = constraints.copy()
        constraints_display["finish_display"] = constraints_display["finish_display"].apply(fmt_date)
        st.dataframe(
            constraints_display.rename(columns={"constraint_code": "Constraint", "finish_display": "Finish"}),
            use_container_width=True, hide_index=True,
        )
        st.download_button("⬇️ Export constraints (CSV)", constraints.to_csv(index=False), file_name="constraint_tracker.csv", mime="text/csv")
