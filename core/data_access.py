"""Convenience accessors that turn the loaded live/baseline XER results into
enriched task tables, cached per-result so every module isn't re-deriving
the same DataFrame on every rerun.
"""
from __future__ import annotations

import streamlit as st

from core.state import get_baseline, get_live, get_settings
from core.tasks import build_enriched_tasks, build_relationships, build_wbs, project_info


def _cache_key(result) -> int:
    return id(result)


def get_live_tasks():
    live = get_live()
    if live is None:
        return None
    key = f"_cache_live_tasks_{_cache_key(live)}"
    if key not in st.session_state:
        st.session_state[key] = build_enriched_tasks(live, get_settings())
    return st.session_state[key]


def get_live_relationships():
    live = get_live()
    if live is None:
        return None
    key = f"_cache_live_rel_{_cache_key(live)}"
    if key not in st.session_state:
        st.session_state[key] = build_relationships(live)
    return st.session_state[key]


def get_baseline_tasks():
    baseline = get_baseline()
    if baseline is None:
        return None
    key = f"_cache_base_tasks_{_cache_key(baseline)}"
    if key not in st.session_state:
        st.session_state[key] = build_enriched_tasks(baseline, get_settings())
    return st.session_state[key]


def get_baseline_relationships():
    baseline = get_baseline()
    if baseline is None:
        return None
    key = f"_cache_base_rel_{_cache_key(baseline)}"
    if key not in st.session_state:
        st.session_state[key] = build_relationships(baseline)
    return st.session_state[key]


def require_live_data(module_name: str = "This module") -> bool:
    live = get_live()
    if live is None or not live.ok:
        st.info(
            f"📥 {module_name} needs a live programme loaded first. "
            "Go to **Module 0 · File Intake** to drop a .xer file (or load the demo programme).",
            icon="📥",
        )
        st.stop()
    return True


def invalidate_settings_dependent_caches() -> None:
    """Call after settings change so discipline/activity-code classification recomputes."""
    for key in list(st.session_state.keys()):
        if key.startswith("_cache_live_tasks_") or key.startswith("_cache_base_tasks_"):
            del st.session_state[key]
