# Copilot instructions for this repository

This repo holds two unrelated things — know which one you're touching:

1. **The personal page** at the repo root (`index.html`, `style/`, `images/`) —
   a static HTML site for a Brazilian technical course assignment (Portuguese
   content). Leave its structure and content conventions as they are.
2. **`Programme Dashboard`** — a Python/Streamlit app for schedule QSRA,
   DCMA assessment, and programme trackers, built from Primavera P6 `.xer`
   exports. This is what most code changes in this repo will touch.

## Programme Dashboard architecture

- **Entry point**: `app.py` is the Streamlit landing page (critical path
  Gantt + programme health summary). Every other module is a file under
  `pages/`, numbered `01_`–`13_` so Streamlit's sidebar orders them
  correctly — keep new pages inside that numeric scheme.
- **`core/`** holds all business logic, kept deliberately separate from the
  `pages/*.py` UI scripts:
  - `xer_parser.py` — generic `%T/%F/%R` XER table parser. Never assume a
    specific project's table shape; flag malformed/missing data instead of
    raising.
  - `tasks.py` — turns raw XER tables into one enriched, analysis-ready
    DataFrame per programme. This is the single source every module reads
    from — don't re-parse raw XER columns in a page file.
  - `settings.py` — every threshold, discipline band, and activity-code
    type name is user-editable here and persisted to
    `data/cache/settings.json`. **Never hardcode a project-specific value**
    (a discipline name, a threshold, an activity code) in a `core/modules/*`
    file — read it from settings instead, so the dashboard stays generic
    across any of Jason's programmes.
  - `state.py` / `data_access.py` — session state, baseline/live XER
    caching, and cached enriched-task accessors. Use `get_live_tasks()` /
    `get_baseline_tasks()` rather than re-deriving from `core.tasks`
    directly inside a page.
  - `theme.py` / `charts.py` — the custom dark/light design system. Use
    `style_fig()` on every Plotly figure before `st.plotly_chart()` so
    charts stay in sync with the theme toggle (a plain `template=` kwarg
    lags a rerun behind — see `core/theme.py`'s docstring for why).
  - `modules/*.py` — one file per numbered module's pure compute logic
    (no Streamlit calls), so it's testable outside the UI.
- **Dates**: always render via `core/dates.py`'s `fmt_date()` /
  `uk_axis_tickformat()` — **DD/MM/YYYY everywhere**, never a bare
  `pd.Timestamp` or default pandas/Plotly formatting in anything the user
  sees. CSV exports may keep ISO dates.
- **No cost/earned-value tracking anywhere** — this is a schedule,
  resource, and contractual-impact tool only. Don't add money fields, even
  to the NEC compensation-event tracker (Module 13 is schedule-impact only
  by design).
- **Generic by construction**: nothing should assume one project's
  discipline names, activity code scheme, or key dates. If a module needs
  new project-specific data, add a setting for it in `core/settings.py`
  rather than a constant in the module.

## Running it

```bash
python3 -m venv venv && source venv/bin/activate   # source venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run app.py
```

Or on Windows, double-click `Launch Dashboard.bat` (self-installing).

There's a synthetic demo XER generator (`core/sample_data.py`, wired into
Module 0's "Load demo programme" buttons) for testing without a real file —
use it rather than fabricating XER fixtures inline.

## Conventions

- Every module page should offer a CSV export button for its main table.
- RAG (red/amber/green) status should use `core/theme.py`'s `rag_badge()` /
  `render_status_card()` helpers, not ad-hoc colour strings.
- Keep `core/modules/*.py` free of `import streamlit` — UI belongs in
  `pages/*.py` and `app.py` only.
