"""Landing page: Module 9 (critical path Gantt) + Module 12 (programme
health summary), combined on one view per the brief.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data_access import get_baseline_tasks, get_live_relationships, get_live_tasks
from core.dates import uk_hoverformat, uk_axis_tickformat
from core.modules.dcma import run_dcma_assessment
from core.modules.gantt_health import compute_programme_health, select_critical_path_activities, select_key_date_milestones
from core.modules.spi import compute_spi_overall
from core.page import bootstrap
from core.state import get_live, get_settings
from core.theme import discipline_color, plotly_template, rag_badge, rag_color, render_status_card, style_fig

bootstrap("Landing", "🏠")

live = get_live()
tasks = get_live_tasks()
settings = get_settings()

if live is None or tasks is None or tasks.empty:
    st.markdown('<div class="pd-section-title">Welcome, Jason 👋</div>', unsafe_allow_html=True)
    st.info(
        "No live programme is loaded yet. Head to **📥 Module 0 · File Intake** in the sidebar to "
        "drop this cycle's live XER (and, first time only, your accepted baseline XER) - or load "
        "the demo programme there to explore the dashboard straight away.",
        icon="👋",
    )
    st.stop()

baseline_tasks = get_baseline_tasks()

# ------------------------------------------------------------ compute health
relationships = get_live_relationships()
data_date_actual = tasks["start_actual"].dropna().max() if tasks["start_actual"].notna().any() else pd.Timestamp.today()

dcma_metrics = run_dcma_assessment(tasks, relationships, settings["dcma_thresholds"], baseline_tasks, data_date_actual)

spi_overall = None
if baseline_tasks is not None and not baseline_tasks.empty:
    spi_overall = compute_spi_overall(tasks, baseline_tasks, data_date_actual)

mc_result = st.session_state.get("mc_result")

key_date_status = st.session_state.get("key_date_status_cache")
if key_date_status is None:
    from core.modules.key_dates import compute_key_date_status
    key_date_status = compute_key_date_status(
        tasks, baseline_tasks if baseline_tasks is not None else pd.DataFrame(),
        settings["key_date_slip_amber_days"], settings["key_date_slip_red_days"],
    )

health = compute_programme_health(dcma_metrics, mc_result, spi_overall, key_date_status)

# ------------------------------------------------------------------- tiles
st.markdown('<div class="pd-section-title">📊 Module 12 — Programme Health Summary</div>', unsafe_allow_html=True)
t1, t2, t3, t4, t5 = st.columns(5)
with t1:
    overall = health["overall"]
    render_status_card("Overall Programme Health", overall.upper(), overall)
with t2:
    d = health["dcma"]
    render_status_card("DCMA 14-Point", d["label"], d["status"], "See Module 2 for detail")
with t3:
    mc = health["monte_carlo"]
    val = mc["p50"].strftime("%d/%m/%Y") if mc["p50"] else "Not run"
    render_status_card("Monte Carlo P50", val, mc["status"], "See Module 1 for detail")
with t4:
    spi = health["spi"]
    val = f"{spi['spi_duration']:.2f}" if spi["spi_duration"] is not None and pd.notna(spi["spi_duration"]) else "N/A"
    render_status_card("SPI (duration)", val, spi["status"], "See Module 5 for detail")
with t5:
    kd = health["key_dates"]
    render_status_card("Key Dates", f"{kd['total'] - kd['red'] - kd['amber']}/{kd['total']} green", kd["status"], "See Module 7 for detail")

st.write("")

col_gantt, col_doughnuts = st.columns([2.2, 1])

with col_gantt:
    st.markdown('<div class="pd-section-title">🛤️ Module 9 — Critical Path Gantt</div>', unsafe_allow_html=True)
    critical = select_critical_path_activities(tasks, max_bars=50)
    milestones = select_key_date_milestones(tasks)

    if critical.empty:
        st.info("No activities with valid dates found to plot.")
    else:
        critical = critical.sort_values("start_display")
        fig = px.timeline(
            critical, x_start="start_display", x_end="finish_display", y="task_code",
            color="discipline", color_discrete_map={d: discipline_color(d) for d in critical["discipline"].unique()},
            hover_data={"task_name": True, "total_float_days": True, "discipline": True},
            template=plotly_template(),
        )
        fig.update_yaxes(autorange="reversed", title="")
        fig.update_xaxes(title="", tickformat=uk_axis_tickformat(), hoverformat=uk_hoverformat())
        for _, m in milestones.iterrows():
            fig.add_vline(x=m["finish_display"], line_dash="dash", line_color="#e0507a", opacity=0.7)
            fig.add_annotation(x=m["finish_display"], y=1.04, yref="paper", showarrow=False,
                                text=m["key_date_code"], font=dict(size=10, color="#e0507a"))
        fig.update_layout(height=max(420, 20 * len(critical)), margin=dict(l=10, r=10, t=40, b=10), legend_title="Discipline")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.caption("Showing the critical path (or lowest-float activities where no negative/zero float exists yet). Dashed lines are key date milestones.")

    csv = critical.drop(columns=[c for c in critical.columns if critical[c].dtype == "bool"], errors="ignore").to_csv(index=False)
    st.download_button("⬇️ Export critical path (CSV)", csv, file_name="critical_path.csv", mime="text/csv")

with col_doughnuts:
    st.markdown('<div class="pd-section-title">Health Breakdown</div>', unsafe_allow_html=True)
    if dcma_metrics:
        counts = health["dcma"]["counts"]
        fig_d = go.Figure(data=[go.Pie(
            labels=["Green", "Amber", "Red", "N/A"],
            values=[counts["green"], counts["amber"], counts["red"], counts["grey"]],
            hole=0.6,
            marker=dict(colors=[rag_color("green"), rag_color("amber"), rag_color("red"), rag_color("grey")]),
        )])
        fig_d.update_layout(template=plotly_template(), height=260, margin=dict(l=10, r=10, t=30, b=10), title="DCMA 14-Point Status", showlegend=True)
        st.plotly_chart(style_fig(fig_d), use_container_width=True)

    if spi_overall is not None and pd.notna(spi_overall[1]):
        spi_count, spi_duration = spi_overall
        fig_s = go.Figure(data=[go.Pie(
            labels=["Earned", "Remaining to target"],
            values=[max(spi_duration, 0), max(1 - spi_duration, 0)],
            hole=0.6,
            marker=dict(colors=[rag_color("green" if spi_duration >= 0.95 else "amber" if spi_duration >= 0.85 else "red"), "#333844"]),
        )])
        fig_s.update_layout(template=plotly_template(), height=260, margin=dict(l=10, r=10, t=30, b=10), title=f"SPI (duration-weighted): {spi_duration:.2f}", showlegend=False)
        st.plotly_chart(style_fig(fig_s), use_container_width=True)
    else:
        st.info("Load a baseline XER to see the SPI doughnut here.")

    kd = health["key_dates"]
    if kd["total"] > 0:
        fig_k = go.Figure(data=[go.Pie(
            labels=["Green", "Amber", "Red"],
            values=[kd["total"] - kd["red"] - kd["amber"], kd["amber"], kd["red"]],
            hole=0.6,
            marker=dict(colors=[rag_color("green"), rag_color("amber"), rag_color("red")]),
        )])
        fig_k.update_layout(template=plotly_template(), height=260, margin=dict(l=10, r=10, t=30, b=10), title="Key Dates Status", showlegend=True)
        st.plotly_chart(style_fig(fig_k), use_container_width=True)
