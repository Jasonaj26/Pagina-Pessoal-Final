"""Generic Primavera P6 .xer file parser.

XER is a plain-text, tab-delimited export format:

    %ERMHDR	<version>	<date>	...
    %T	TASK
    %F	task_id	proj_id	task_code	...
    %R	1001	100	A1000	...
    %R	1002	100	A1010	...
    %T	TASKPRED
    %F	task_pred_id	...
    %R	...

This module parses *every* table it finds into a pandas DataFrame (keyed
by table name), not just the four the brief calls out by name - PROJWBS,
PROJECT, TASK and TASKPRED are the ones the rest of the dashboard depends
on directly, but activity-code tables (ACTVTYPE / ACTVCODE / TASKACTV) and
CALENDAR are what let every other module stay "generic, driven by
activity codes" rather than hardcoded to one project, so we keep them
too whenever the source file includes them.

Malformed data (row/column count mismatches, missing required tables,
unreadable encoding) is collected as warnings/errors rather than raised,
per the "flag, don't fail silently" requirement.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

REQUIRED_TABLES = ["PROJECT", "PROJWBS", "TASK", "TASKPRED"]
OPTIONAL_TABLES = ["CALENDAR", "ACTVTYPE", "ACTVCODE", "TASKACTV", "RSRC", "TASKRSRC"]


@dataclass
class XerParseResult:
    tables: Dict[str, pd.DataFrame] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_filename: Optional[str] = None
    project_name: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.errors and all(t in self.tables for t in REQUIRED_TABLES)

    def missing_required(self) -> List[str]:
        return [t for t in REQUIRED_TABLES if t not in self.tables]

    def table(self, name: str) -> pd.DataFrame:
        return self.tables.get(name, pd.DataFrame())


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def parse_xer(raw: bytes, filename: Optional[str] = None) -> XerParseResult:
    result = XerParseResult(source_filename=filename)

    if not raw or not raw.strip():
        result.errors.append(f"'{filename}' is empty.")
        return result

    text = _decode(raw)
    lines = text.splitlines()

    if not lines or not lines[0].startswith("%ERMHDR"):
        result.warnings.append(
            f"'{filename}' does not start with the expected %ERMHDR header - "
            "this may not be a valid .xer export."
        )

    current_table: Optional[str] = None
    current_fields: List[str] = []
    current_rows: List[List[str]] = []
    malformed_row_counts: Dict[str, int] = {}

    def flush():
        if current_table and current_fields:
            df = pd.DataFrame(current_rows, columns=current_fields)
            result.tables[current_table] = df

    for line_no, line in enumerate(lines, start=1):
        if not line:
            continue
        parts = line.split("\t")
        tag = parts[0]

        if tag == "%T":
            flush()
            current_table = parts[1].strip() if len(parts) > 1 else None
            current_fields = []
            current_rows = []
        elif tag == "%F":
            current_fields = [p.strip() for p in parts[1:]]
        elif tag == "%R":
            if current_table is None or not current_fields:
                continue
            values = parts[1:]
            if len(values) != len(current_fields):
                malformed_row_counts[current_table] = malformed_row_counts.get(current_table, 0) + 1
                # pad/truncate so we don't lose the whole table over one bad row
                if len(values) < len(current_fields):
                    values = values + [""] * (len(current_fields) - len(values))
                else:
                    values = values[: len(current_fields)]
            current_rows.append(values)
        elif tag == "%E":
            continue  # end of file marker
        # unrecognised tags (e.g. %ERMHDR handled above) are ignored

    flush()

    for table_name, bad_count in malformed_row_counts.items():
        result.warnings.append(
            f"Table {table_name}: {bad_count} row(s) had a different column count than "
            f"the %F header and were padded/truncated - check the source export."
        )

    missing = [t for t in REQUIRED_TABLES if t not in result.tables]
    if missing:
        result.errors.append(
            f"'{filename}' is missing required table(s): {', '.join(missing)}. "
            "Re-export the .xer making sure these tables are included."
        )

    for t in REQUIRED_TABLES:
        if t in result.tables and result.tables[t].empty:
            result.warnings.append(f"Table {t} was found but contains zero rows.")

    if "PROJECT" in result.tables and not result.tables["PROJECT"].empty:
        proj_df = result.tables["PROJECT"]
        name_col = next((c for c in ("proj_short_name", "proj_name") if c in proj_df.columns), None)
        if name_col:
            result.project_name = str(proj_df.iloc[0][name_col])

    return result


def get_calendar_ids(result: XerParseResult) -> List[str]:
    """Distinct calendar IDs actually in use by tasks (for mismatch detection)."""
    task_df = result.table("TASK")
    if task_df.empty or "clndr_id" not in task_df.columns:
        return []
    return sorted(task_df["clndr_id"].dropna().unique().tolist())


def get_calendar_names(result: XerParseResult) -> Dict[str, str]:
    cal_df = result.table("CALENDAR")
    if cal_df.empty or "clndr_id" not in cal_df.columns:
        return {}
    name_col = "clndr_name" if "clndr_name" in cal_df.columns else None
    if not name_col:
        return {}
    return dict(zip(cal_df["clndr_id"], cal_df[name_col]))
