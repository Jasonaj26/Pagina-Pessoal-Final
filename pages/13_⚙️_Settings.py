"""Central settings/config panel. Every threshold, discipline band, and
activity-code mapping used anywhere in the dashboard is editable here -
none of it is hardcoded in the module source.
"""
import pandas as pd
import streamlit as st

from core.data_access import invalidate_settings_dependent_caches
from core.modules.crew_sizing import QUANTITY_COLUMNS
from core.page import bootstrap
from core.settings import reset_settings, save_settings
from core.state import get_settings
from core.store import load_table, save_table

bootstrap("Settings", "⚙️")
st.markdown('<div class="pd-section-title">⚙️ Settings & Configuration</div>', unsafe_allow_html=True)
st.caption("Everything here is project-agnostic and persisted locally, so the same dashboard works across all of Jason's live programmes.")

settings = get_settings()

tabs = st.tabs([
    "Monte Carlo bands", "Discipline classification", "DCMA thresholds",
    "Crew production rates", "Key dates & activity codes", "General",
])

with tabs[0]:
    st.subheader("Discipline uncertainty bands (± %)")
    bands = settings["monte_carlo"]["discipline_bands_pct"]
    cols = st.columns(3)
    new_bands = {}
    for i, (disc, pct) in enumerate(bands.items()):
        with cols[i % 3]:
            new_bands[disc] = st.number_input(disc, min_value=0, max_value=100, value=int(pct), key=f"band_{disc}")
    settings["monte_carlo"]["discipline_bands_pct"] = new_bands

    st.subheader("Simulation settings")
    settings["monte_carlo"]["iterations"] = st.number_input(
        "Iterations (minimum 10,000)", min_value=10000, max_value=200000,
        value=int(settings["monte_carlo"]["iterations"]), step=1000,
    )
    levels = st.text_input("Confidence levels (comma-separated)", value=", ".join(str(x) for x in settings["monte_carlo"]["confidence_levels"]))
    try:
        settings["monte_carlo"]["confidence_levels"] = [int(x.strip()) for x in levels.split(",") if x.strip()]
    except ValueError:
        st.error("Confidence levels must be a comma-separated list of numbers, e.g. 50, 80, 90")

with tabs[1]:
    st.subheader("Discipline activity code type")
    settings["discipline_activity_code_type"] = st.text_input(
        "ACTVTYPE name used for discipline classification", value=settings["discipline_activity_code_type"]
    )
    st.subheader("Fallback keyword classification")
    st.caption("Used only for activities that don't carry the discipline activity code above.")
    kw = settings["discipline_keywords"]
    for disc in list(kw.keys()):
        kw[disc] = [w.strip() for w in st.text_input(f"{disc} keywords (comma-separated)", value=", ".join(kw[disc]), key=f"kw_{disc}").split(",") if w.strip()]
    settings["discipline_keywords"] = kw

with tabs[2]:
    st.subheader("DCMA 14-point thresholds")
    th = settings["dcma_thresholds"]
    c1, c2 = st.columns(2)
    keys = list(th.keys())
    for i, k in enumerate(keys):
        with (c1 if i % 2 == 0 else c2):
            th[k] = st.number_input(k.replace("_", " ").title(), value=float(th[k]), key=f"dcma_{k}")
    settings["dcma_thresholds"] = th

with tabs[3]:
    st.subheader("Crew production rates (no defaults assumed)")
    st.caption("Define units-per-crew-per-day for each discipline you want Module 4 to size crews for.")
    rates = settings["crew_production_rates"]
    disciplines = list(settings["monte_carlo"]["discipline_bands_pct"].keys())
    for disc in disciplines:
        with st.expander(disc, expanded=disc in rates):
            existing = rates.get(disc, {})
            unit = st.text_input("Unit", value=existing.get("unit", ""), key=f"unit_{disc}")
            rate = st.number_input("Rate per crew per day", min_value=0.0, value=float(existing.get("rate_per_crew", 0.0)), key=f"rate_{disc}")
            if unit or rate:
                rates[disc] = {"unit": unit, "rate_per_crew": rate}
    settings["crew_production_rates"] = rates

    st.divider()
    st.subheader("Remaining quantities (this cycle)")
    qty_df = load_table("crew_sizing_quantities", QUANTITY_COLUMNS)
    if qty_df.empty:
        qty_df = pd.DataFrame({"discipline": disciplines, "remaining_quantity": ["0"] * len(disciplines)})
    edited_qty = st.data_editor(qty_df, num_rows="dynamic", use_container_width=True, key="qty_editor")
    if st.button("Save remaining quantities"):
        save_table("crew_sizing_quantities", edited_qty)
        st.success("Saved.")

with tabs[4]:
    st.subheader("Generic activity-code type names")
    st.caption("These map to ACTVTYPE names in your XER exports - change them if your P6 setup uses different labels.")
    settings["key_date_activity_code_type"] = st.text_input("Key date activity code type", value=settings["key_date_activity_code_type"])
    settings["interface_activity_code_type"] = st.text_input("Interface activity code type", value=settings["interface_activity_code_type"])
    settings["constraint_activity_code_type"] = st.text_input("Constraint activity code type", value=settings["constraint_activity_code_type"])
    settings["ifc_package_activity_code_type"] = st.text_input("IFC package activity code type", value=settings["ifc_package_activity_code_type"])
    settings["procurement_package_activity_code_type"] = st.text_input("Procurement package activity code type", value=settings["procurement_package_activity_code_type"])
    settings["ce_link_activity_code_type"] = st.text_input("Compensation event activity code type", value=settings["ce_link_activity_code_type"])

    st.divider()
    st.subheader("Key date RAG thresholds (days late vs baseline)")
    settings["key_date_slip_amber_days"] = st.number_input("Amber threshold (days)", min_value=0, value=int(settings["key_date_slip_amber_days"]))
    settings["key_date_slip_red_days"] = st.number_input("Red threshold (days)", min_value=0, value=int(settings["key_date_slip_red_days"]))

    st.divider()
    st.subheader("IFC / Procurement warning windows")
    settings["ifc_warning_days"] = st.number_input("IFC buffer warning (days)", min_value=0, value=int(settings["ifc_warning_days"]))
    settings["procurement_at_risk_days"] = st.number_input("Procurement at-risk buffer (days)", min_value=0, value=int(settings["procurement_at_risk_days"]))

with tabs[5]:
    settings["user_name"] = st.text_input("Name shown in the header", value=settings.get("user_name", "Jason Jackson"))
    st.divider()
    if st.button("🔄 Reset all settings to defaults", type="secondary"):
        st.session_state.settings = reset_settings()
        st.rerun()

if st.button("💾 Save settings", type="primary"):
    save_settings(settings)
    st.session_state.settings = settings
    invalidate_settings_dependent_caches()
    st.success("Settings saved and applied.")
