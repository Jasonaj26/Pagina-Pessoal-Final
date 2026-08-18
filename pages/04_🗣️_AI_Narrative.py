"""Module 3: AI Narrative Layer (rule-based, fully local, no external APIs)."""
import pandas as pd
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_relationships, get_live_tasks, require_live_data
from core.history import load_key_date_history
from core.modules.dcma import run_dcma_assessment
from core.modules.key_dates import compute_key_date_status, consecutive_slip_flags
from core.modules.narrative import build_full_narrative
from core.modules.spi import compute_spi_by_discipline
from core.page import bootstrap
from core.state import get_settings

bootstrap("Module 3 · AI Narrative", "🗣️")
require_live_data("AI Narrative Layer")

st.markdown('<div class="pd-section-title">🗣️ Module 3 — AI Narrative Layer</div>', unsafe_allow_html=True)
st.caption("Rule-based, plain-English schedule health observations. Runs entirely locally - no external API calls, no LLM dependency.")

tasks = get_live_tasks()
relationships = get_live_relationships()
baseline_tasks = get_baseline_tasks()
settings = get_settings()
data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()

dcma_metrics = st.session_state.get("dcma_metrics") or run_dcma_assessment(
    tasks, relationships, settings["dcma_thresholds"], baseline_tasks, data_date
)
mc_result = st.session_state.get("mc_result")

spi_by_discipline = None
if baseline_tasks is not None and not baseline_tasks.empty:
    spi_by_discipline = compute_spi_by_discipline(tasks, baseline_tasks, data_date)

key_date_status = compute_key_date_status(
    tasks, baseline_tasks if baseline_tasks is not None else pd.DataFrame(),
    settings["key_date_slip_amber_days"], settings["key_date_slip_red_days"],
)
kd_history = load_key_date_history()
slip_flags = consecutive_slip_flags(kd_history)

narrative = build_full_narrative(
    dcma_metrics=dcma_metrics, mc_result=mc_result, deterministic_finish=tasks["finish_display"].max(),
    spi_by_discipline=spi_by_discipline, key_date_status=key_date_status, slip_flags=slip_flags,
)

for category, sentences in narrative.items():
    st.markdown(f"#### {category}")
    for s in sentences:
        st.markdown(f"- {s}")
    st.write("")

all_text = "\n\n".join(f"{cat}\n" + "\n".join(f"- {s}" for s in sents) for cat, sents in narrative.items())
st.download_button("⬇️ Export narrative (TXT)", all_text, file_name="schedule_narrative.txt", mime="text/plain")
