# X-SHIELD paper repo

This repo contains:
- `data/scenarios/`: JSONL scenario event logs (8 required scenarios)
- `explainer/`: Auto-Explainer CLI to generate X-SHIELD JSON + teacher summaries
- `data/xshield_outputs/`: generated outputs

Generate outputs:
```bash
python3 explainer/explainer.py --in data/scenarios --out data/xshield_outputs
