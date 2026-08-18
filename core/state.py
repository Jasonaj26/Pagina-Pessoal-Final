"""Session-state wiring + baseline caching.

Module 0 requires the baseline XER to be cached locally so only the live
XER needs re-uploading each reporting cycle. We persist the parsed
baseline (not just the raw file) as a pickle in data/cache/, and restore
it into st.session_state automatically on app start. The live XER is also
mirrored to disk (a separate, session-scoped cache) purely so an
accidental browser refresh mid-cycle doesn't force Jason to re-drop it.
"""
from __future__ import annotations

import os
import pickle

import streamlit as st

from core.settings import load_settings
from core.xer_parser import XerParseResult

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
BASELINE_CACHE_PATH = os.path.join(CACHE_DIR, "baseline.pkl")
LIVE_CACHE_PATH = os.path.join(CACHE_DIR, "live_session.pkl")


def init_session_state() -> None:
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
    if "live_result" not in st.session_state:
        st.session_state.live_result = _load_pickle(LIVE_CACHE_PATH)
    if "baseline_result" not in st.session_state:
        st.session_state.baseline_result = _load_pickle(BASELINE_CACHE_PATH)
    if "theme" not in st.session_state:
        st.session_state.theme = st.session_state.settings.get("theme", "dark")


def _load_pickle(path: str) -> XerParseResult | None:
    if os.path.exists(path):
        try:
            with open(path, "rb") as fh:
                return pickle.load(fh)
        except (pickle.PickleError, EOFError, OSError, AttributeError):
            return None
    return None


def cache_baseline(result: XerParseResult) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(BASELINE_CACHE_PATH, "wb") as fh:
        pickle.dump(result, fh)
    st.session_state.baseline_result = result


def clear_cached_baseline() -> None:
    if os.path.exists(BASELINE_CACHE_PATH):
        os.remove(BASELINE_CACHE_PATH)
    st.session_state.baseline_result = None


def set_live(result: XerParseResult) -> None:
    st.session_state.live_result = result
    # Cached per-session (not the durable cycle-to-cycle cache baseline gets) purely so
    # an accidental browser refresh mid-cycle doesn't force a re-upload.
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(LIVE_CACHE_PATH, "wb") as fh:
        pickle.dump(result, fh)


def get_live() -> XerParseResult | None:
    return st.session_state.get("live_result")


def get_baseline() -> XerParseResult | None:
    return st.session_state.get("baseline_result")


def get_settings() -> dict:
    return st.session_state.settings
