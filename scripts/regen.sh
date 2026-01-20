#!/usr/bin/env bash
set -euo pipefail

rm -f data/xshield_outputs/*
python3 explainer/explainer.py --in data/scenarios --out data/xshield_outputs
python3 -c "import glob,json; [json.load(open(p)) for p in glob.glob('data/xshield_outputs/*_xshield.json')]; print('All JSON OK')"
echo "Regenerated outputs in data/xshield_outputs/"
