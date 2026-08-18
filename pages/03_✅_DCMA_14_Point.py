"""Module 2: DCMA 14-Point Assessment."""
import pandas as pd
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_relationships, get_live_tasks, require_live_data
from core.modules.dcma import run_dcma_assessment, summary_counts
from core.page import bootstrap
from core.state import get_settings
from core.theme import rag_badge

bootstrap("Module 2 · DCMA 14-Point", "✅")
require_live_data("DCMA 14-Point Assessment")

st.markdown('<div class="pd-section-title">✅ Module 2 — DCMA 14-Point Assessment</div>', unsafe_allow_html=True)

tasks = get_live_tasks()
relationships = get_live_relationships()
baseline_tasks = get_baseline_tasks()
settings = get_settings()

data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()
metrics = run_dcma_assessment(tasks, relationships, settings["dcma_thresholds"], baseline_tasks, data_date)
st.session_state.dcma_metrics = metrics

counts = summary_counts(metrics)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"### 🟢 {counts['green']}\nPassing")
c2.markdown(f"### 🟠 {counts['amber']}\nBorderline")
c3.markdown(f"### 🔴 {counts['red']}\nFailing")
c4.markdown(f"### ⚪ {counts['grey']}\nNot applicable")

st.divider()

for row_start in range(0, len(metrics), 2):
    cols = st.columns(2)
    for col, m in zip(cols, metrics[row_start:row_start + 2]):
        with col:
            st.markdown(
                f"""
                <div class="pd-card" style="margin-bottom:1rem;">
                    <div class="pd-card-title">#{m.number} · {m.name}</div>
                    <div class="pd-card-value">{m.result_display} {rag_badge(m.status)}</div>
                    <div class="pd-card-subtitle">{m.description}<br/>Threshold: {m.threshold_display}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if m.note:
                st.caption(f"ℹ️ {m.note}")
            if m.failing_ids:
                with st.expander(f"{len(m.failing_ids)} failing activity ID(s)"):
                    st.write(", ".join(m.failing_ids))
                    st.download_button(
                        f"⬇️ Export failing IDs — {m.name}",
                        "\n".join(["task_code"] + m.failing_ids),
                        file_name=f"dcma_{m.number}_{m.name.replace(' ', '_')}_failing.csv",
                        mime="text/csv",
                        key=f"dl_{m.number}",
                    )

st.divider()
all_failing = pd.DataFrame(
    [(m.number, m.name, tid) for m in metrics for tid in m.failing_ids],
    columns=["metric_number", "metric_name", "task_code"],
)
st.download_button(
    "⬇️ Export full failing activity list (all metrics)", all_failing.to_csv(index=False),
    file_name="dcma_all_failing_activities.csv", mime="text/csv", disabled=all_failing.empty,
)
