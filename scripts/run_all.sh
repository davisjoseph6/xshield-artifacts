#!/usr/bin/env bash
set -euo pipefail

# Ensure we are in repo root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Activate venv if present
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[1/3] Regenerate X-SHIELD outputs + validate schema"
bash scripts/regen.sh

echo "[2/3] Generate demo study results"
python study/make_demo_results.py --out study/results.csv --n_participants 8

echo "[3/3] Analyze study results and export figures"
python study/analyze.py --in study/results.csv --out paper/figures

echo
echo "DONE."
echo "Outputs:"
echo " - data/xshield_outputs/"
echo " - study/results.csv"
echo " - paper/figures/"
