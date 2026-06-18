#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source venv/bin/activate

python3 main_v5.py update-universe \
  --config config_v5.yaml \
  --universe-csv data/universe/UTIL_carteira_atual.csv
