@echo off
REM ============================================================
REM  Launch Dashboard.bat
REM  Double-click this file at any time to launch Jason's
REM  Programme Dashboard. No terminal knowledge required.
REM
REM  What it does:
REM    1. Looks for a "venv" virtual environment next to this file.
REM       If it isn't there yet (first run, or after a fresh clone),
REM       it creates one automatically.
REM    2. Activates the virtual environment.
REM    3. Installs/updates the required packages from requirements.txt
REM       (fast no-op if already installed).
REM    4. Launches the Streamlit app and opens it in your default
REM       web browser.
REM ============================================================

setlocal
cd /d "%~dp0"

echo ============================================
echo   Jason Jackson - Programme Dashboard
echo ============================================
echo.

REM --- Guard against Windows' 260-character path limit ---------
REM Some packages (Streamlit included) install deeply-nested internal
REM files. Combined with a long folder name - especially the doubled
REM "reponame-branchname\reponame-branchname" folder that "Extract All"
REM sometimes creates from a downloaded ZIP - this can blow past
REM Windows' classic MAX_PATH limit and fail deep inside pip install
REM with a confusing error. Catch it here instead, with a clear fix.
for /f %%L in ('powershell -NoProfile -Command "(Get-Location).Path.Length" 2^>nul') do set CURDIR_LEN=%%L
if defined CURDIR_LEN if %CURDIR_LEN% GTR 80 (
    echo [WARNING] This folder's path is quite long:
    echo             %cd%
    echo.
    echo           Windows has a 260-character path limit, and some packages
    echo           install deeply-nested files that can exceed it from a long
    echo           starting path - the failure shows up as a confusing pip
    echo           error later, not a clear message here.
    echo.
    echo           To avoid this, move this whole folder somewhere short and
    echo           shallow first - for example straight onto C:\ as C:\Dash -
    echo           then run this file again from there.
    echo.
    echo           Continuing anyway in 5 seconds... ^(Ctrl+C to stop and move it^)
    timeout /t 5 >nul
)

REM --- Locate a Python 3 launcher -----------------------------
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY_LAUNCHER=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PY_LAUNCHER=python"
    ) else (
        echo [ERROR] Python 3 was not found on this PC.
        echo Please install Python 3 from https://www.python.org/downloads/
        echo and tick "Add python.exe to PATH" during setup, then try again.
        pause
        exit /b 1
    )
)

REM --- Create the venv if it does not exist yet ---------------
if not exist "venv\Scripts\activate.bat" (
    echo [Setup] Creating virtual environment "venv" ... this only happens once.
    %PY_LAUNCHER% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

REM --- Activate the venv ---------------------------------------
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment.
    pause
    exit /b 1
)

REM --- Install / update required packages -----------------------
echo [Setup] Checking required packages ...
echo          If these are not installed yet, this downloads Streamlit,
echo          pandas, NumPy and Plotly - it can take a few minutes the
echo          first time depending on your internet connection. You will
echo          see progress bars below while it works. Already installed?
echo          This step finishes in a couple of seconds.
echo.
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip. Check your internet connection.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install required packages. Check your internet connection.
    pause
    exit /b 1
)

REM --- Launch the dashboard and open the browser -----------------
echo.
echo [Launch] Starting the dashboard ... your browser will open automatically.
echo          Close this window to stop the dashboard.
echo.

start "" http://localhost:8501

streamlit run app.py --server.headless false --server.port 8501

endlocal
