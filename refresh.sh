#!/bin/bash
# Rebuilds everything from the copied Box Office Mojo tables, in order. Safe to rerun (API calls are cached).
#   ./refresh.sh            full rebuild + backtest + draft forecasts
#   ./refresh.sh --quick    skip the backtest (just refresh data and forecasts)
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY pipeline/build_films.py
$PY pipeline/tmdb_enrich.py
$PY pipeline/upcoming.py
$PY pipeline/features.py
[ "$1" = "--quick" ] || $PY models/backtest.py > /dev/null && echo "backtest -> docs/backtest_summary.md"
$PY models/forecast_live.py
echo "Done. Dashboard: .venv/bin/streamlit run app/dashboard.py"
