# Jason Jackson — Programme Dashboard

A local, self-contained Streamlit dashboard for Primavera P6 (.xer) schedule
QSRA, DCMA 14-point health checks, performance tracking and contractual
trackers — built generically off activity codes so the same app works
across all of Jason's live programmes.

## Quick start (Windows)

1. Double-click **`Launch Dashboard.bat`** in this folder.
2. First run only: it creates a `venv` virtual environment and installs
   everything it needs (Streamlit, pandas, Plotly, NumPy). This takes a
   minute or two and needs an internet connection once; every run after
   that is instant.
3. Your browser opens automatically at `http://localhost:8501`.
4. To stop the dashboard, close the black command-window that opened
   alongside the browser tab.

No terminal knowledge is required — the batch file does everything.

## First-time setup

1. Go to **📥 Module 0 · File Intake** in the sidebar.
2. Drop your **baseline** XER on the right — it's cached locally (in
   `data/cache/`) so you only need to do this once. Use **Clear cached
   baseline** there if you ever need to replace it.
3. Every reporting cycle after that, just drop the current **live** XER on
   the left.
4. No XER handy? Use the **Load demo programme** buttons at the bottom of
   Module 0 to explore every module with clearly-labelled synthetic data.

## Configuring it for a project

Everything project-specific lives in **⚙️ Settings** — discipline
uncertainty bands, DCMA thresholds, crew production rates, and the
*activity code type names* that drive the generic trackers (key dates,
interfaces, constraints, IFC packages, procurement packages, NEC CEs).
Nothing is hardcoded in the module source, so pointing Settings at a new
programme's activity code scheme is all that's needed to reuse the
dashboard on a different job.

For the activity-code-driven trackers (Modules 7, 8, 10, 11, 13) to link
correctly, tag the relevant activities in P6 with the matching activity
code **on both sides of the relationship** — e.g. give the IFC issuance
activities and the construction activities that need them the same IFC
package code value.

## What's where

| Page | Module |
|---|---|
| Landing (`app.py`) | Module 9 (critical path Gantt) + Module 12 (programme health summary) |
| 📥 File Intake | Module 0 |
| 🎲 Monte Carlo QSRA | Module 1 |
| ✅ DCMA 14-Point | Module 2 |
| 🗣️ AI Narrative | Module 3 (rule-based, fully offline — no external API calls) |
| 👷 Crew/Gang Sizing | Module 4 |
| 📊 SPI by Discipline | Module 5 |
| 📈 Resource Histogram | Module 6 |
| 🗓️ Key Date Tracking | Module 7 |
| 🔗 Interface & Constraint Tracker | Module 8 |
| 📐 IFC Drawing Tracker | Module 10 |
| 📦 Procurement Tracker | Module 11 |
| ⚖️ NEC Compensation Events | Module 13 (schedule impact only — no cost/value tracking anywhere) |
| ⚙️ Settings | Central config panel |

All dates throughout are shown as **DD/MM/YYYY**. Every module has a
download/export button for its data.

## Cycle-on-cycle trend charts (Modules 5 & 7)

The SPI trend S-curve and key-date movement S-curve are built from your
own successive submissions — each time you load a new live XER in Module 0
(with a baseline already cached), a snapshot is recorded to
`data/cache/programme_history.csv` and `data/cache/key_date_history.csv`.
The trend fills in as you use the dashboard cycle over cycle; a single
cycle just shows one point.

## Notes on this build

- Runs entirely locally — no data leaves your machine, no external APIs.
- The Monte Carlo engine, DCMA checks, and trackers are a genuine
  implementation (real PERT-beta simulation over your TASK/TASKPRED
  network, real DCMA formulas), simplified in places a full commercial
  risk/scheduling tool would go further (e.g. single-calendar Monte Carlo,
  no resource levelling) — flagged in-app where relevant.
- If your XER export doesn't include TASKRSRC resource assignments,
  Module 6 falls back to a concurrent-activity-count proxy and says so.
