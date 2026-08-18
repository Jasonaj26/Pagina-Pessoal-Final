"""Module 5: SPI by Discipline."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_tasks, require_live_data
from core.dates import fmt_date, uk_axis_tickformat, uk_hoverformat
from core.history import load_programme_history
from core.modules.spi import compute_spi_by_discipline, compute_spi_overall
from core.page import bootstrap
from core.theme import discipline_color, plotly_template, rag_color, style_fig

bootstrap("Module 5 · SPI by Discipline", "📊")
require_live_data("SPI by Discipline")

st.markdown('<div class="pd-section-title">📊 Module 5 — SPI by Discipline</div>', unsafe_allow_html=True)

tasks = get_live_tasks()
baseline_tasks = get_baseline_tasks()

if baseline_tasks is None or baseline_tasks.empty:
    st.info("📥 Load a baseline XER in Module 0 to compute SPI against it.", icon="📥")
    st.stop()

data_date = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()
spi_df = compute_spi_by_discipline(tasks, baseline_tasks, data_date)
spi_count_overall, spi_duration_overall = compute_spi_overall(tasks, baseline_tasks, data_date)

m1, m2 = st.columns(2)
m1.metric("Overall SPI — activity count", f"{spi_count_overall:.2f}" if pd.notna(spi_count_overall) else "N/A")
m2.metric("Overall SPI — duration-weighted", f"{spi_duration_overall:.2f}" if pd.notna(spi_duration_overall) else "N/A")

if spi_df.empty:
    st.info("No activities are baselined to be complete by the current data date yet.")
    st.stop()

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.markdown("##### SPI — Activity Count")
    fig = go.Figure(data=[go.Pie(
        labels=spi_df["discipline"], values=spi_df["spi_count"], hole=0.55,
        marker=dict(colors=[discipline_color(d) for d in spi_df["discipline"]]),
    )])
    fig.update_layout(template=plotly_template(), height=380)
    st.plotly_chart(style_fig(fig), use_container_width=True)
with col2:
    st.markdown("##### SPI — Duration Weighted")
    fig2 = go.Figure(data=[go.Pie(
        labels=spi_df["discipline"], values=spi_df["spi_duration"], hole=0.55,
        marker=dict(colors=[discipline_color(d) for d in spi_df["discipline"]]),
    )])
    fig2.update_layout(template=plotly_template(), height=380)
    st.plotly_chart(style_fig(fig2), use_container_width=True)

st.divider()
st.markdown("##### Schedule Variance by Discipline")
fig3 = go.Figure()
fig3.add_bar(x=spi_df["discipline"], y=spi_df["sv_days"], name="SV (working days)", marker_color="#e0507a")
fig3.add_bar(x=spi_df["discipline"], y=spi_df["sv_count"], name="SV (activity count)", marker_color="#f5a623")
fig3.update_layout(template=plotly_template(), barmode="group", height=380)
st.plotly_chart(style_fig(fig3), use_container_width=True)

st.dataframe(spi_df, use_container_width=True, hide_index=True)
st.download_button("⬇️ Export SPI by discipline (CSV)", spi_df.to_csv(index=False), file_name="spi_by_discipline.csv", mime="text/csv")

st.divider()
st.markdown("##### SPI Trend Over Time (S-Curve)")
history = load_programme_history()
if history.empty or len(history) < 2:
    st.info("Trend builds as you load each cycle's live XER in Module 0 - only one cycle recorded so far.")
    if not history.empty:
        history_display = history.copy()
        history_display["data_date"] = history_display["data_date"].apply(fmt_date)
        st.dataframe(history_display, use_container_width=True, hide_index=True)
else:
    fig4 = go.Figure()
    fig4.add_scatter(x=history["data_date"], y=history["spi_count_overall"], mode="lines+markers", name="SPI (count)", line_color="#4f8cff")
    fig4.add_scatter(x=history["data_date"], y=history["spi_duration_overall"], mode="lines+markers", name="SPI (duration)", line_color="#38c172")
    fig4.add_hline(y=1.0, line_dash="dot", line_color="#9aa0ab")
    fig4.update_layout(template=plotly_template(), height=380, yaxis_title="SPI",
                        xaxis=dict(title="Data date", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()))
    st.plotly_chart(style_fig(fig4), use_container_width=True)
