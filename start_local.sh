#!/usr/bin/env bash
# One-command local launch: runs the pipeline once, then opens the
# dashboard as a live webapp at http://localhost:8501
#
# Usage:
#   ./start_local.sh                 # dry-run (uses existing data/*.csv), then dashboard
#   ./start_local.sh --live          # actually scrapes playstore+amazon+reddit first
#   ./start_local.sh --watch         # runs pipeline in background every hour while dashboard stays open
set -e

cd "$(dirname "$0")"

MODE="dry"
WATCH=false
for arg in "$@"; do
  case $arg in
    --live) MODE="live" ;;
    --watch) WATCH=true ;;
  esac
done

echo "=== boAt Sentiment System — Local Launch ==="

if [ "$MODE" = "live" ]; then
  echo "[1/2] Running full pipeline (live scraping + sentiment + topics + AI summary)..."
  python3 orchestrator.py --sources playstore amazon
else
  echo "[1/2] Running pipeline in dry-run mode (existing data in data/*.csv)..."
  python3 orchestrator.py --dry-run
fi

if [ "$WATCH" = true ]; then
  echo "Starting background refresh (re-runs pipeline every hour)..."
  ( python3 orchestrator.py --schedule hourly $([ "$MODE" = "live" ] && echo "--sources playstore amazon" || echo "--dry-run") > logs/background_watch.log 2>&1 & )
  echo "Background refresh started — logs at logs/background_watch.log"
fi

echo "[2/2] Launching dashboard at http://localhost:8501 ..."
cd dashboard
streamlit run app.py
