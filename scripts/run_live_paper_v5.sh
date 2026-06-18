#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source venv/bin/activate
mkdir -p logs state/live state/paper

python3 main_v5.py live-cycle \
  --config config_v5.yaml \
  --benchmark-csv data/benchmarks/UTIL_historico.csv \
  --universe-csv data/universe/UTIL_carteira_atual.csv \
  --update-universe-first \
  --mode paper \
  --apply-paper-targets \
  --output-dir state/live \
  >> logs/live_paper_v5.log 2>&1
