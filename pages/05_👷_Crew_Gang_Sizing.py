"""Module 4: Crew/Gang Sizing to hold P50."""
import pandas as pd
import streamlit as st

from core.data_access import get_live_tasks, require_live_data
from core.dates import fmt_date
from core.modules.crew_sizing import QUANTITY_COLUMNS, build_crew_plan
from core.page import bootstrap
from core.state import get_settings
from core.store import load_table, save_table

bootstrap("Module 4 · Crew/Gang Sizing", "👷")
require_live_data("Crew/Gang Sizing")

st.markdown('<div class="pd-section-title">👷 Module 4 — Crew/Gang Sizing to Hold P50</div>', unsafe_allow_html=True)
st.caption("Uses Jason's own production rate inputs - no assumed defaults. Rates are defined per discipline in ⚙️ Settings.")

tasks = get_live_tasks()
settings = get_settings()
rates = settings["crew_production_rates"]

mc_result = st.session_state.get("mc_result")
if mc_result is not None and 50 in mc_result.percentiles:
    p50_date = mc_result.percentiles[50]
    p50_source = "Monte Carlo P50 (Module 1)"
else:
    p50_date = tasks["finish_display"].max()
    p50_source = "Deterministic programme finish (run Module 1 for a risk-adjusted P50)"

data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()

st.info(f"Target date to hold: **{fmt_date(p50_date)}** ({p50_source})", icon="🎯")

if not rates:
    st.warning("No production rates defined yet. Go to ⚙️ Settings → Crew production rates to enter units-per-crew-per-day for each discipline.", icon="⚠️")

st.markdown("##### Remaining quantity of work (this cycle)")
disciplines = list(settings["monte_carlo"]["discipline_bands_pct"].keys())
qty_df = load_table("crew_sizing_quantities", QUANTITY_COLUMNS)
if qty_df.empty:
    qty_df = pd.DataFrame({"discipline": disciplines, "remaining_quantity": ["0"] * len(disciplines)})
edited = st.data_editor(qty_df, num_rows="dynamic", use_container_width=True, key="crew_qty_editor")
if st.button("💾 Save quantities"):
    save_table("crew_sizing_quantities", edited)
    st.success("Saved.")

plan = build_crew_plan(edited, rates, p50_date, data_date)

st.divider()
st.markdown("##### Crew/gang sizing plan")
if plan.empty:
    st.info("Add remaining quantities above to see the required crew sizes.")
else:
    display = plan.copy()
    display["crews_required"] = display["crews_required"].fillna("Set a rate in Settings")
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Export crew sizing plan (CSV)", plan.to_csv(index=False), file_name="crew_sizing_plan.csv", mime="text/csv")
