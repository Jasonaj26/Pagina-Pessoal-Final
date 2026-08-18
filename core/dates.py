"""UK date formatting helpers.

Every date shown anywhere in the dashboard must render as DD/MM/YYYY.
Never use pandas/streamlit/plotly defaults (which tend to be US style)
without piping through these helpers first.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional, Union

import pandas as pd

UK_DATE_FORMAT = "%d/%m/%Y"
UK_DATETIME_FORMAT = "%d/%m/%Y %H:%M"

DateLike = Union[str, _dt.date, _dt.datetime, pd.Timestamp, None]


def to_timestamp(value: DateLike) -> Optional[pd.Timestamp]:
    """Best-effort conversion of an XER-style or arbitrary date value to a Timestamp."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value
    if isinstance(value, (_dt.date, _dt.datetime)):
        return pd.Timestamp(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "nat"}:
            return None
        # XER dates commonly look like 2025-06-30 08:00 or 2025-06-30
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return pd.Timestamp(_dt.datetime.strptime(text, fmt))
            except ValueError:
                continue
        try:
            return pd.Timestamp(text)
        except (ValueError, TypeError):
            return None
    try:
        ts = pd.Timestamp(value)
        return None if pd.isna(ts) else ts
    except (ValueError, TypeError):
        return None


def fmt_date(value: DateLike, placeholder: str = "—") -> str:
    """Format any date-like value as DD/MM/YYYY, or a placeholder if unavailable."""
    ts = to_timestamp(value)
    if ts is None:
        return placeholder
    return ts.strftime(UK_DATE_FORMAT)


def fmt_datetime(value: DateLike, placeholder: str = "—") -> str:
    ts = to_timestamp(value)
    if ts is None:
        return placeholder
    return ts.strftime(UK_DATETIME_FORMAT)


def uk_axis_tickformat() -> str:
    """Plotly tickformat string for UK-style date axes."""
    return "%d/%m/%Y"


def uk_hoverformat() -> str:
    return "%d/%m/%Y"
