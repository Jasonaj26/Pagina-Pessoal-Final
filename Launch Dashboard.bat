@echo off
REM Double-click to launch the Programme Dashboard. First run creates a
REM venv and installs requirements.txt; later runs just start the app.

setlocal
cd /d "%~dp0"

echo ============================================
echo   Jason Jackson - Programme Dashboard
echo ============================================
echo.

REM Warn if the path is long enough to risk Windows' 260-char limit
REM (can otherwise fail deep inside pip install with a confusing error).
for /f %%L in ('powershell -NoProfile -Command "(Get-Location).Path.Length" 2^>nul') do set CURDIR_LEN=%%L
if defined CURDIR_LEN if %CURDIR_LEN% GTR 80 (
    echo [WARNING] This folder's path is long and may hit Windows' 260-character
    echo           limit during install. If setup fails, move this folder
    echo           somewhere short like C:\Dash and run this file again.
    echo           Continuing in 5 seconds...
    timeout /t 5 >nul
)

REM Find a Python 3 launcher
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY_LAUNCHER=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PY_LAUNCHER=python"
    ) else (
        echo [ERROR] Python 3 not found. Install it from python.org,
        echo         ticking "Add python.exe to PATH", then try again.
        pause
        exit /b 1
    )
)

REM Create the venv on first run
if not exist "venv\Scripts\activate.bat" (
    echo [Setup] Creating virtual environment "venv" ...
    %PY_LAUNCHER% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Could not activate the virtual environment.
    pause
    exit /b 1
)

REM Install/update packages (visible progress; skip if already current)
echo [Setup] Checking required packages - first run can take a few minutes...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed. Check your internet connection.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Package install failed. Check your internet connection.
    pause
    exit /b 1
)

REM Launch
echo.
echo [Launch] Starting the dashboard - your browser will open automatically.
echo          Close this window to stop it.
start "" http://localhost:8501
streamlit run app.py --server.headless false --server.port 8501

endlocal
