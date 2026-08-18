"""Module 6: Aggregate Resource Histogram."""
import pandas as pd
import streamlit as st

from core.data_access import get_live_tasks, require_live_data
from core.dates import fmt_date, uk_axis_tickformat, uk_hoverformat
from core.modules.resource_histogram import compute_resource_histogram, flag_over_allocation
from core.page import bootstrap
from core.state import get_live, get_settings
from core.theme import discipline_color, plotly_template, style_fig
import plotly.graph_objects as go

bootstrap("Module 6 · Resource Histogram", "📈")
require_live_data("Resource Histogram")

st.markdown('<div class="pd-section-title">📈 Module 6 — Aggregate Resource Histogram</div>', unsafe_allow_html=True)

tasks = get_live_tasks()
live = get_live()
settings = get_settings()

period = st.radio("Period", ["Weekly", "Monthly"], horizontal=True)
period_code = "W" if period == "Weekly" else "M"

histogram, used_real = compute_resource_histogram(tasks, live, period=period_code)

if not used_real:
    st.info(
        "No TASKRSRC resource assignments found in this XER export - showing a concurrent-activity-count "
        "proxy by discipline instead of true resource loading.",
        icon="ℹ️",
    )

if histogram.empty:
    st.info("No active, dated tasks available to build a histogram.")
    st.stop()

st.markdown("##### Define discipline capacity (optional, for over-allocation highlighting)")
disciplines = sorted(histogram["discipline"].unique())
cap_cols = st.columns(min(len(disciplines), 5) or 1)
capacity = {}
for i, disc in enumerate(disciplines):
    with cap_cols[i % len(cap_cols)]:
        val = st.number_input(f"{disc} capacity", min_value=0.0, value=0.0, key=f"cap_{disc}")
        if val > 0:
            capacity[disc] = val

flagged = flag_over_allocation(histogram, capacity)

fig = go.Figure()
for disc in disciplines:
    sub = flagged[flagged["discipline"] == disc]
    fig.add_bar(x=sub["period"], y=sub["demand"], name=disc, marker_color=discipline_color(disc))

fig.update_layout(template=plotly_template(), barmode="stack", height=460, yaxis_title="Demand", xaxis=dict(title="Period", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()))

over_periods = flagged[flagged["over_allocated"]]["period"].unique()
period_width = pd.Timedelta(days=7) if period_code == "W" else pd.Timedelta(days=30)
for p in over_periods:
    fig.add_vrect(x0=p, x1=p + period_width, fillcolor="red", opacity=0.12, line_width=0)

st.plotly_chart(style_fig(fig), use_container_width=True)
if len(over_periods) > 0:
    st.error(f"⚠️ {len(over_periods)} period(s) exceed defined capacity - highlighted in red.", icon="⚠️")

flagged_display = flagged.copy()
flagged_display["period"] = flagged_display["period"].apply(fmt_date)
st.dataframe(flagged_display, use_container_width=True, hide_index=True)
st.download_button("⬇️ Export resource histogram (CSV)", flagged.to_csv(index=False), file_name="resource_histogram.csv", mime="text/csv")
