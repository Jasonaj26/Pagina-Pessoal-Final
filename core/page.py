"""Common page bootstrap: config, theme, session state, persistent header."""
from __future__ import annotations

import streamlit as st

from core.header import render_header
from core.state import init_session_state
from core.theme import apply_theme


def bootstrap(page_title: str, page_icon: str = "📊", layout: str = "wide") -> None:
    st.set_page_config(page_title=f"{page_title} · Programme Dashboard", page_icon=page_icon, layout=layout)
    init_session_state()
    # The header renders the dark/light toggle, which updates
    # st.session_state.theme as a side effect - apply_theme() must run
    # *after* that so the injected CSS reflects this run's chosen theme
    # rather than lagging a run behind.
    render_header()
    apply_theme()
