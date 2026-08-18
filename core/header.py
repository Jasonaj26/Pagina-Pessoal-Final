"""Persistent header shown at the top of every page: Jason Jackson's name,
plus the live and baseline programme names pulled straight from each
loaded XER's PROJECT table. Updates automatically whenever either file
changes.
"""
from __future__ import annotations

import streamlit as st

from core.settings import save_settings
from core.state import get_baseline, get_live, get_settings
from core.tasks import project_info
from core.xer_parser import get_calendar_ids, get_calendar_names


def _programme_label(result) -> tuple[str, str]:
    if result is None:
        return "Not loaded", ""
    info = project_info(result)
    name = info.get("name") or info.get("long_name") or result.project_name or "(unnamed project)"
    sub = result.source_filename or ""
    return name, sub


def render_header() -> None:
    settings = get_settings()
    live = get_live()
    baseline = get_baseline()

    live_name, live_file = _programme_label(live)
    base_name, base_file = _programme_label(baseline)

    col_main, col_toggle = st.columns([6, 1])
    with col_main:
        st.markdown(
            f"""
            <div class="pd-header">
                <div>
                    <div class="pd-header-sub">Programme Dashboard</div>
                    <div class="pd-header-name">👤 {settings.get('user_name', 'Jason Jackson')}</div>
                </div>
                <div class="pd-header-programmes">
                    <div>
                        <div class="pd-header-sub">Live Programme</div>
                        <div class="pd-header-prog-value">{live_name}</div>
                    </div>
                    <div>
                        <div class="pd-header-sub">Baseline Programme</div>
                        <div class="pd-header-prog-value">{base_name}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_toggle:
        is_dark = st.session_state.get("theme", "dark") == "dark"
        if st.toggle("🌙 Dark", value=is_dark, key="theme_toggle"):
            st.session_state.theme = "dark"
        else:
            st.session_state.theme = "light"
        if st.session_state.theme != settings.get("theme"):
            settings["theme"] = st.session_state.theme
            save_settings(settings)

    _calendar_mismatch_banner(live, baseline)


def _calendar_mismatch_banner(live, baseline) -> None:
    if live is None or baseline is None:
        return
    live_ids = set(get_calendar_ids(live))
    base_ids = set(get_calendar_ids(baseline))
    live_names = get_calendar_names(live)
    base_names = get_calendar_names(baseline)

    live_name_set = {live_names.get(i, i) for i in live_ids} if live_names else live_ids
    base_name_set = {base_names.get(i, i) for i in base_ids} if base_names else base_ids

    if live_name_set and base_name_set and live_name_set != base_name_set:
        st.warning(
            "⚠️ **Calendar mismatch detected** - the live and baseline XERs use different "
            f"calendars (live: {', '.join(sorted(map(str, live_name_set)))} | "
            f"baseline: {', '.join(sorted(map(str, base_name_set)))}). "
            "Durations/dates compared across the two may not be like-for-like.",
            icon="⚠️",
        )
