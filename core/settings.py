"""Central, user-editable configuration for the dashboard.

Nothing that varies project-to-project should be hardcoded in the module
source. Everything here is persisted to data/cache/settings.json and can
be changed from the Settings page at any time.
"""
from __future__ import annotations

import copy
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "settings.json")

DEFAULT_SETTINGS = {
    # ---- Module 1: Monte Carlo QSRA -----------------------------------
    "monte_carlo": {
        "iterations": 10000,
        "confidence_levels": [50, 80, 90],
        # +/- percentage uncertainty applied to remaining duration, by discipline
        "discipline_bands_pct": {
            "Civils": 20,
            "Procurement": 30,
            "Commissioning": 20,
            "Construction/Installation": 25,
            "Engineering": 15,
            "Other": 15,
        },
    },
    # ---- Discipline classification (drives Modules 1, 5, 6, 9) --------
    "discipline_activity_code_type": "Discipline",
    # fallback keyword match against activity ID / name when no activity
    # code of the type above is assigned to a task
    "discipline_keywords": {
        "Civils": ["CIV", "CIVIL", "GROUND", "EARTHWORK"],
        "Procurement": ["PROC", "PURCH", "ORDER", "PO-"],
        "Commissioning": ["COMM", "TEST", "HANDOVER"],
        "Construction/Installation": ["CONST", "INSTALL", "BUILD", "ERECT"],
        "Engineering": ["ENG", "DESIGN", "IFC", "DRAWING"],
        "Other": [],
    },
    # ---- Module 2: DCMA 14-point thresholds ----------------------------
    "dcma_thresholds": {
        "logic_missing_pct_max": 5.0,
        "leads_count_max": 0,
        "lags_count_max": 5,
        "fs_relationship_pct_min": 90.0,
        "hard_constraints_count_max": 5,
        "high_float_days": 44,
        "high_float_pct_max": 5.0,
        "negative_float_count_max": 0,
        "high_duration_days": 44,
        "high_duration_pct_max": 5.0,
        "invalid_dates_count_max": 0,
        "resources_missing_pct_max": 15.0,
        "missed_activities_pct_max": 5.0,
        "critical_path_test_days": 600,
        "cpli_min": 0.95,
        "baseline_execution_index_min": 0.95,
    },
    # ---- Module 4: Crew / gang sizing ----------------------------------
    # Production rate per activity code / discipline. No defaults assumed -
    # Jason enters units-per-crew-per-day for each discipline he needs.
    "crew_production_rates": {
        # "Civils": {"unit": "m3/day", "rate_per_crew": 0.0},
    },
    # ---- Module 7: Key dates -------------------------------------------
    "key_date_activity_code_type": "KeyDate",
    "key_date_slip_amber_days": 5,
    "key_date_slip_red_days": 10,
    # ---- Module 8: Interfaces & constraints -----------------------------
    "interface_activity_code_type": "Interface",
    "constraint_activity_code_type": "Constraint",
    # ---- Module 10: IFC drawing tracker ----------------------------------
    "ifc_package_activity_code_type": "IFCPackage",
    "ifc_warning_days": 10,
    # ---- Module 11: Procurement & long lead ------------------------------
    "procurement_package_activity_code_type": "ProcPackage",
    "procurement_at_risk_days": 5,
    # ---- Module 13: NEC compensation events ------------------------------
    "ce_link_activity_code_type": "CENumber",
    # ---- Appearance -------------------------------------------------------
    "theme": "dark",
    "user_name": "Jason Jackson",
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> dict:
    """Load settings, seeded with defaults for any missing keys."""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            return _deep_merge(DEFAULT_SETTINGS, saved)
        except (json.JSONDecodeError, OSError):
            pass
    return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)


def reset_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        os.remove(SETTINGS_PATH)
    return copy.deepcopy(DEFAULT_SETTINGS)
