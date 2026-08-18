"""Custom visual theme: dark/light palettes, card/tile components, and the
persistent header. Deliberately not default Streamlit styling.
"""
from __future__ import annotations

import streamlit as st

RAG_COLORS = {
    "red": {"bg": "#3a1414", "bg_light": "#fdecea", "fg": "#ff6b6b", "fg_light": "#c62828", "label": "Red"},
    "amber": {"bg": "#3a2c0f", "bg_light": "#fff6e0", "fg": "#ffc857", "fg_light": "#b8860b", "label": "Amber"},
    "green": {"bg": "#12321f", "bg_light": "#e8f5e9", "fg": "#4ade80", "fg_light": "#2e7d32", "label": "Green"},
    "grey": {"bg": "#26282f", "bg_light": "#eceff1", "fg": "#9aa0ab", "fg_light": "#607080", "label": "N/A"},
}

DARK = {
    "bg": "#0f1116",
    "bg_panel": "#171a21",
    "bg_card": "#1c2029",
    "border": "#2a2e39",
    "text": "#e8eaed",
    "text_muted": "#9aa0ab",
    "accent": "#4f8cff",
    "accent_soft": "#1c2b4a",
}

LIGHT = {
    "bg": "#f5f7fa",
    "bg_panel": "#ffffff",
    "bg_card": "#ffffff",
    "border": "#e1e5ec",
    "text": "#1a1d24",
    "text_muted": "#5b6270",
    "accent": "#2f6fed",
    "accent_soft": "#e8f0ff",
}

DISCIPLINE_COLORS = {
    "Civils": "#4f8cff",
    "Procurement": "#f5a623",
    "Commissioning": "#38c172",
    "Construction/Installation": "#e0507a",
    "Engineering": "#9b6bff",
    "Other": "#9aa0ab",
}


def palette() -> dict:
    return DARK if st.session_state.get("theme", "dark") == "dark" else LIGHT


def plotly_template() -> str:
    return "plotly_dark" if st.session_state.get("theme", "dark") == "dark" else "plotly_white"


def style_fig(fig):
    """Force explicit paper/plot background + font colour from our palette.

    Passing template="plotly_dark"/"plotly_white" alone can lag a run behind
    the CSS toggle (Streamlit's own chrome and Plotly's template resolution
    don't always repaint in the same rerun) - setting these explicitly on
    every figure keeps charts perfectly in sync with the rest of the page.
    """
    p = palette()
    fig.update_layout(
        paper_bgcolor=p["bg_card"], plot_bgcolor=p["bg_card"],
        font_color=p["text"], legend_font_color=p["text"],
    )
    fig.update_xaxes(gridcolor=p["border"], zerolinecolor=p["border"], linecolor=p["border"])
    fig.update_yaxes(gridcolor=p["border"], zerolinecolor=p["border"], linecolor=p["border"])
    return fig


def discipline_color(discipline: str) -> str:
    return DISCIPLINE_COLORS.get(discipline, "#9aa0ab")


def rag_color(status: str, dark: bool | None = None) -> str:
    status = status.lower()
    is_dark = st.session_state.get("theme", "dark") == "dark" if dark is None else dark
    entry = RAG_COLORS.get(status, RAG_COLORS["grey"])
    return entry["fg"] if is_dark else entry["fg_light"]


def apply_theme() -> None:
    p = palette()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {p['bg']};
            color: {p['text']};
        }}
        html, body, [class*="css"] {{
            font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
        }}
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div,
        div[data-testid="stSidebarContent"], div[data-testid="stSidebarUserContent"] {{
            background-color: {p['bg_panel']} !important;
            border-right: 1px solid {p['border']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {p['text']};
        }}
        div[data-testid="stHeader"], div[data-testid="stAppViewContainer"], div[data-testid="stMain"] {{
            background-color: transparent !important;
        }}
        div[data-testid="stExpander"], div[data-testid="stMetric"], div[data-testid="stDataFrame"],
        div[data-testid="stFileUploader"] section {{
            background-color: {p['bg_card']};
            border: 1px solid {p['border']};
            border-radius: 10px;
        }}
        div.stButton > button, div.stDownloadButton > button {{
            background-color: {p['bg_card']};
            color: {p['text']};
            border: 1px solid {p['border']};
        }}
        .pd-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            background: {p['bg_panel']};
            border: 1px solid {p['border']};
            border-radius: 14px;
            padding: 0.9rem 1.4rem;
            margin-bottom: 1.2rem;
        }}
        .pd-header-name {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {p['text']};
        }}
        .pd-header-sub {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {p['text_muted']};
            margin-bottom: 0.1rem;
        }}
        .pd-header-programmes {{
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }}
        .pd-header-prog-value {{
            font-size: 1rem;
            font-weight: 600;
            color: {p['accent']};
        }}
        .pd-card {{
            background: {p['bg_card']};
            border: 1px solid {p['border']};
            border-radius: 14px;
            padding: 1rem 1.2rem;
            height: 100%;
        }}
        .pd-card-title {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {p['text_muted']};
            margin-bottom: 0.35rem;
        }}
        .pd-card-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {p['text']};
            line-height: 1.2;
        }}
        .pd-card-subtitle {{
            font-size: 0.78rem;
            color: {p['text_muted']};
            margin-top: 0.3rem;
        }}
        .pd-status-dot {{
            display: inline-block;
            width: 0.6rem;
            height: 0.6rem;
            border-radius: 50%;
            margin-right: 0.4rem;
        }}
        .pd-badge {{
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }}
        .pd-section-title {{
            font-size: 1.05rem;
            font-weight: 700;
            margin: 0.4rem 0 0.6rem 0;
            color: {p['text']};
        }}
        div.stButton > button {{
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_card(title: str, value: str, status: str = "grey", subtitle: str = "") -> str:
    p = palette()
    color = rag_color(status)
    entry = RAG_COLORS.get(status.lower(), RAG_COLORS["grey"])
    return f"""
    <div class="pd-card" style="border-left: 4px solid {color};">
        <div class="pd-card-title">{title}</div>
        <div class="pd-card-value">
            <span class="pd-status-dot" style="background:{color};"></span>{value}
        </div>
        <div class="pd-card-subtitle">{subtitle}</div>
    </div>
    """


def render_status_card(title: str, value: str, status: str = "grey", subtitle: str = "") -> None:
    st.markdown(status_card(title, value, status, subtitle), unsafe_allow_html=True)


def rag_badge(status: str) -> str:
    color = rag_color(status)
    entry = RAG_COLORS.get(status.lower(), RAG_COLORS["grey"])
    is_dark = st.session_state.get("theme", "dark") == "dark"
    bg = entry["bg"] if is_dark else entry["bg_light"]
    return f'<span class="pd-badge" style="background:{bg};color:{color};">{status.upper()}</span>'
