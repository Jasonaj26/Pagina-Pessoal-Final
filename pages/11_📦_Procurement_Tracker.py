"""Module 11: Procurement & Long-Lead Item Tracker."""
import pandas as pd
import plotly.express as px
import streamlit as st

from core.data_access import get_live_tasks, require_live_data
from core.dates import fmt_date, uk_axis_tickformat, uk_hoverformat
from core.modules.procurement import build_procurement_status
from core.page import bootstrap
from core.state import get_settings
from core.theme import plotly_template, rag_color, style_fig

bootstrap("Module 11 · Procurement Tracker", "📦")
require_live_data("Procurement & Long-Lead Item Tracker")

st.markdown('<div class="pd-section-title">📦 Module 11 — Procurement & Long-Lead Item Tracker</div>', unsafe_allow_html=True)

tasks = get_live_tasks()
settings = get_settings()

status = build_procurement_status(tasks, settings["procurement_at_risk_days"])

if status.empty:
    st.info(f"No activities tagged with the '{settings['procurement_package_activity_code_type']}' activity code.", icon="ℹ️")
    st.stop()

at_risk = status[status["status"].isin(["red", "amber"])]
if not at_risk.empty:
    st.error(f"⚠️ {len(at_risk)} package(s) at risk of impacting the programme.", icon="⚠️")

st.markdown("##### Procurement Gantt")
gantt_df = status.dropna(subset=["order_start", "delivery_date"]).copy()
if not gantt_df.empty:
    fig = px.timeline(
        gantt_df, x_start="order_start", x_end="delivery_date", y="package", color="status",
        color_discrete_map={"green": rag_color("green"), "amber": rag_color("amber"), "red": rag_color("red"), "grey": rag_color("grey")},
        template=plotly_template(),
    )
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title="", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat())
    for _, r in gantt_df.dropna(subset=["need_by"]).iterrows():
        fig.add_vline(x=r["need_by"], line_dash="dot", line_color="#e0507a")
    fig.update_layout(height=max(300, 40 * len(gantt_df)), margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(style_fig(fig), use_container_width=True)
    st.caption("Dotted red lines mark when construction/commissioning needs the item.")

display = status.copy()
for c in ["order_start", "delivery_date", "need_by"]:
    display[c] = display[c].apply(fmt_date)
st.dataframe(display, use_container_width=True, hide_index=True)
st.download_button("⬇️ Export procurement tracker (CSV)", status.to_csv(index=False), file_name="procurement_tracker.csv", mime="text/csv")
