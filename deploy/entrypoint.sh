#!/bin/sh
# Starts the ESD Memory demo.
# The data volume is the app's database: JSON files (memories, chats, state)
# and an SQLite file (embedding cache). Everything is created on first use.
set -e

DATA="${ESD_DATA_DIR:-/app/data}"
mkdir -p "$DATA"

# First start only: copy in the ready-made demo snapshot,
# so "Load demo history" is instant instead of rebuilding it.
if [ ! -f "$DATA/demo_snapshot/meta.json" ]; then
  mkdir -p "$DATA/demo_snapshot"
  cp /app/deploy/demo_snapshot/*.json "$DATA/demo_snapshot/"
fi

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true \
  --browser.gatherUsageStats=false
