"""Module 13: NEC Compensation Event Tracker.

Schedule impact and status tracking only. No cost or value tracking
anywhere in this module or the wider platform.
"""
import pandas as pd
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_tasks, require_live_data
from core.modules.ce_tracker import CE_REGISTER_COLUMNS, ce_headline_counts, summarize_ce
from core.page import bootstrap
from core.store import load_table, save_table
from core.theme import rag_badge

bootstrap("Module 13 · NEC Compensation Events", "⚖️")
require_live_data("NEC Compensation Event Tracker")

st.markdown('<div class="pd-section-title">⚖️ Module 13 — NEC Compensation Event Tracker</div>', unsafe_allow_html=True)
st.caption("Schedule impact and status tracking only — no cost or value tracking anywhere in this module or the wider platform.")

tasks = get_live_tasks()
baseline_tasks = get_baseline_tasks()

st.markdown("##### CE Register")
register = load_table("ce_register", CE_REGISTER_COLUMNS)
if register.empty:
    register = pd.DataFrame(columns=CE_REGISTER_COLUMNS)
edited = st.data_editor(
    register, num_rows="dynamic", use_container_width=True, key="ce_editor",
    column_config={
        "status": st.column_config.SelectboxColumn(options=["Open", "Closed"]),
        "notified_impact_days": st.column_config.NumberColumn(),
        "date_notified": st.column_config.DateColumn(format="DD/MM/YYYY"),
    },
)
if st.button("💾 Save CE register"):
    save_table("ce_register", edited)
    st.success("Saved.")

ce_df = summarize_ce(edited, tasks, baseline_tasks)
counts = ce_headline_counts(ce_df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Open CEs", counts["open"])
c2.metric("Closed CEs", counts["closed"])
c3.metric("Notified impact not yet in baseline (days)", int(counts["impact_not_reflected_days"]))
c4.metric("CEs with no logic change in live programme", counts["flagged_no_logic"])

st.divider()
if not ce_df.empty:
    if counts["flagged_no_logic"] > 0:
        st.error(
            f"⚠️ {counts['flagged_no_logic']} CE(s) have a notified programme impact but no corresponding "
            f"logic change ('{tasks.attrs.get('ce_link_activity_code_type', '')}' activity code) found in the "
            "live programme - check whether these have actually been incorporated.",
            icon="⚠️",
        )
    display = ce_df.copy()
    display["flag_no_logic_change"] = display["flag_no_logic_change"].map(lambda x: rag_badge("red") if x else rag_badge("green"))
    st.write(display.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.download_button("⬇️ Export CE tracker (CSV)", ce_df.to_csv(index=False), file_name="ce_tracker.csv", mime="text/csv")
else:
    st.info("Add compensation events to the register above to see status tracking here.")
