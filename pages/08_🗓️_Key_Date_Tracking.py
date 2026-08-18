"""Module 7: Key Date Cycle-on-Cycle Trend Tracking."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_tasks, require_live_data
from core.dates import fmt_date, uk_axis_tickformat, uk_hoverformat
from core.history import load_key_date_history
from core.modules.key_dates import compute_key_date_status, consecutive_slip_flags
from core.page import bootstrap
from core.state import get_settings
from core.theme import plotly_template, rag_badge, style_fig

bootstrap("Module 7 · Key Date Tracking", "🗓️")
require_live_data("Key Date Tracking")

st.markdown('<div class="pd-section-title">🗓️ Module 7 — Key Date Trend Tracking</div>', unsafe_allow_html=True)

tasks = get_live_tasks()
baseline_tasks = get_baseline_tasks()
settings = get_settings()

status_df = compute_key_date_status(
    tasks, baseline_tasks if baseline_tasks is not None else pd.DataFrame(),
    settings["key_date_slip_amber_days"], settings["key_date_slip_red_days"],
)

if status_df.empty:
    st.info(
        f"No activities are tagged with the '{settings['key_date_activity_code_type']}' activity code. "
        "Set this up in ⚙️ Settings if your key dates use a different code type name.",
        icon="ℹ️",
    )
    st.stop()

history = load_key_date_history()
slip_flags = consecutive_slip_flags(history)
status_df = status_df.merge(slip_flags, on="key_date_name", how="left")
status_df["consecutive_slips"] = status_df["consecutive_slips"].fillna(0)

st.markdown("##### Status per key date")
cols = st.columns(min(len(status_df), 4) or 1)
for i, (_, row) in enumerate(status_df.iterrows()):
    with cols[i % len(cols)]:
        st.markdown(
            f"""
            <div class="pd-card">
                <div class="pd-card-title">{row['key_date_name']}</div>
                <div class="pd-card-value">{fmt_date(row['forecast_date'])} {rag_badge(row['status'])}</div>
                <div class="pd-card-subtitle">Baseline: {fmt_date(row['baseline_date'])}<br/>
                Variance: {int(row['variance_days']) if pd.notna(row['variance_days']) else 'N/A'} days
                {"· 🔁 " + str(int(row['consecutive_slips'])) + " consecutive slips" if row['consecutive_slips'] >= 2 else ""}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()
st.markdown("##### Cycle-on-cycle movement (S-curve)")
if history.empty:
    st.info("Trend builds automatically each time you load a new live XER in Module 0.")
else:
    fig = go.Figure()
    for name, grp in history.groupby("key_date_name"):
        grp = grp.sort_values("data_date")
        fig.add_scatter(x=grp["data_date"], y=grp["forecast_date"], mode="lines+markers", name=name)
    fig.update_layout(
        template=plotly_template(), height=420,
        xaxis=dict(title="Reporting cycle (data date)", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()),
        yaxis=dict(title="Forecast key date", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()),
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)
    history_display = history.copy()
    for c in ["data_date", "forecast_date", "baseline_date"]:
        history_display[c] = history_display[c].apply(fmt_date)
    st.dataframe(history_display, use_container_width=True, hide_index=True)

st.download_button("⬇️ Export key date status (CSV)", status_df.to_csv(index=False), file_name="key_date_status.csv", mime="text/csv")
