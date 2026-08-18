"""Module 1: Monte Carlo QSRA."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.charts import labelled_vline
from core.data_access import get_live_relationships, get_live_tasks, require_live_data
from core.dates import fmt_date, uk_axis_tickformat, uk_hoverformat
from core.modules.monte_carlo import run_monte_carlo, tornado_drivers
from core.page import bootstrap
from core.state import get_settings
from core.theme import plotly_template, style_fig

bootstrap("Module 1 · Monte Carlo QSRA", "🎲")
require_live_data("Monte Carlo QSRA")

st.markdown('<div class="pd-section-title">🎲 Module 1 — Monte Carlo QSRA</div>', unsafe_allow_html=True)
st.caption(
    "PERT-beta distributed durations sampled per activity (uncertainty band by discipline, editable "
    "in Settings), propagated across the real TASK/TASKPRED network logic."
)

tasks = get_live_tasks()
relationships = get_live_relationships()
settings = get_settings()
mc_settings = settings["monte_carlo"]

with st.expander("Discipline uncertainty bands in use (edit in ⚙️ Settings)"):
    st.table(pd.DataFrame(list(mc_settings["discipline_bands_pct"].items()), columns=["Discipline", "± %"]))

col_run, col_iter = st.columns([1, 3])
with col_run:
    run_clicked = st.button("▶️ Run simulation", type="primary", use_container_width=True)
with col_iter:
    st.metric("Iterations configured", f"{mc_settings['iterations']:,}")

if run_clicked:
    with st.spinner(f"Running {mc_settings['iterations']:,} iterations across {len(tasks):,} activities..."):
        result = run_monte_carlo(
            tasks, relationships, mc_settings["discipline_bands_pct"],
            iterations=int(mc_settings["iterations"]), confidence_levels=mc_settings["confidence_levels"],
        )
        st.session_state.mc_result = result

result = st.session_state.get("mc_result")

if result is None:
    st.info("Click **Run simulation** to generate the probability distribution, S-curve and tornado chart.")
    st.stop()

for w in result.warnings:
    st.warning(w, icon="⚠️")

st.markdown("#### Completion date percentiles")
pcols = st.columns(len(result.percentiles))
for col, (p, date) in zip(pcols, sorted(result.percentiles.items())):
    with col:
        st.metric(f"P{p}", fmt_date(date))

st.divider()
col_hist, col_scurve = st.columns(2)

with col_hist:
    st.markdown("##### Distribution of Completion Dates")
    finish_dates = result.data_date + pd.to_timedelta(result.finish_offsets_days, unit="D")
    fig = go.Figure(data=[go.Histogram(x=finish_dates, nbinsx=40, marker_color="#4f8cff")])
    for p, color in zip([50, 80, 90], ["#38c172", "#f5a623", "#e0507a"]):
        if p in result.percentiles:
            labelled_vline(fig, result.percentiles[p], color, f"P{p}")
    fig.update_layout(template=plotly_template(), height=380, xaxis_title="Completion date", yaxis_title="Iterations",
                       xaxis=dict(tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()))
    st.plotly_chart(style_fig(fig), use_container_width=True)

with col_scurve:
    st.markdown("##### Cumulative Probability (S-Curve)")
    sorted_offsets = pd.Series(result.finish_offsets_days).sort_values().reset_index(drop=True)
    cum_prob = (sorted_offsets.index + 1) / len(sorted_offsets) * 100
    dates = result.data_date + pd.to_timedelta(sorted_offsets, unit="D")
    fig2 = go.Figure(data=[go.Scatter(x=dates, y=cum_prob, mode="lines", fill="tozeroy", line_color="#4f8cff")])
    for p, color in zip([50, 80, 90], ["#38c172", "#f5a623", "#e0507a"]):
        if p in result.percentiles:
            labelled_vline(fig2, result.percentiles[p], color, f"P{p}")
    fig2.update_layout(template=plotly_template(), height=380, xaxis_title="Completion date", yaxis_title="Cumulative probability (%)",
                        xaxis=dict(tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat()))
    st.plotly_chart(style_fig(fig2), use_container_width=True)

st.divider()
st.markdown("##### 🎯 Tornado Chart — Top Driving Activities")
st.caption("Ranked by correlation between each activity's simulated duration and overall programme completion.")
tornado = tornado_drivers(result, tasks, top_n=12)
if tornado.empty:
    st.info("Not enough variation in the simulation to identify driving activities.")
else:
    tornado = tornado.sort_values("correlation")
    fig3 = go.Figure(go.Bar(
        x=tornado["correlation"], y=tornado["task_code"] + " — " + tornado["task_name"].str.slice(0, 40),
        orientation="h",
        marker_color=["#e0507a" if c > 0 else "#4f8cff" for c in tornado["correlation"]],
    ))
    fig3.update_layout(template=plotly_template(), height=420, xaxis_title="Correlation with programme completion", yaxis_title="")
    st.plotly_chart(style_fig(fig3), use_container_width=True)
    st.dataframe(tornado, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Export tornado drivers (CSV)", tornado.to_csv(index=False) if not tornado.empty else "",
    file_name="monte_carlo_tornado.csv", mime="text/csv", disabled=tornado.empty,
)
