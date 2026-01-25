#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Activate venv if present
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[check] python version:"
python3 --version

echo "[check] compileall:"
python3 -m compileall -q .

echo "[check] regenerate + validate:"
bash scripts/regen.sh

echo "[check] demo study + figures:"
python3 study/make_demo_results.py --out study/results.csv --n_participants 8
python3 study/analyze.py --in study/results.csv --out paper/figures

echo "[check] outputs:"
ls -lh data/xshield_outputs study/results.csv paper/figures

echo "ALL CHECKS PASSED."
