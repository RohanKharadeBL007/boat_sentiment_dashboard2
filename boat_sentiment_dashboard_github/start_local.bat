@echo off
REM One-command local launch for Windows: runs the pipeline once, then
REM opens the dashboard as a live webapp at http://localhost:8501
REM
REM Usage:
REM   start_local.bat            (dry-run, uses existing data\*.csv)
REM   start_local.bat --live     (actually scrapes playstore+amazon+reddit first)

cd /d "%~dp0"

echo === boAt Sentiment System — Local Launch ===

if "%1"=="--live" (
    echo [1/2] Running full pipeline live...
    python orchestrator.py --sources playstore amazon reddit
) else (
    echo [1/2] Running pipeline in dry-run mode...
    python orchestrator.py --dry-run
)

echo [2/2] Launching dashboard at http://localhost:8501 ...
cd dashboard
streamlit run app.py
