## Quickstart (Ubuntu)

### 1) Setup venv
```bash
sudo apt update
sudo apt install -y python3-venv python3-full
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

### 2) Generate X-SHIELD outputs and validate
```bash
bash scripts/regen.sh
```

### 3) Run the viewer
```bash
streamlit run viewer/app.py
```
- Open http://localhost:8501

### 4) Run the study pipeline (demo)
```bash
python3 study/make_demo_results.py --out study/results.csv --n_participants 8
python3 study/analyze.py --in study/results.csv --out paper/figures
```

### 5) One-command end-to-end
```bash
bash scripts/run_all.sh
```

---

## 6) Final “completion checklist”
Run these and confirm they succeed:

```bash
bash scripts/regen.sh
python3 scripts/validate_schema.py
python3 -c "import json,glob; [json.load(open(p)) for p in glob.glob('data/xshield_outputs/*_xshield.json')]; print('json ok')"
python3 study/make_demo_results.py --out study/results.csv --n_participants 8
python3 study/analyze.py --in study/results.csv --out paper/figures
ls -lh data/xshield_outputs study/results.csv paper/figures
```
