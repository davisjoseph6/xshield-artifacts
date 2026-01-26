# X-SHIELD: Explainability-by-Design for Self-Healing Multi-Agent Orchestration in Adaptive Quizzes

**X-SHIELD** is an *explainability-by-design* layer for **self-healing multi-agent orchestration** in **adaptive quiz** settings.

Instead of asking teachers/operators to interpret raw telemetry (logs/metrics/traces), X-SHIELD turns each self-healing intervention into a **first-class, auditable episode artifact** with a clear “explanation contract”:

> **trigger → curated evidence → diagnosis (+ uncertainty) → recovery action → expected effect + post-check → audit metadata**

The repo includes:
1) a **structured JSON schema** (the explanation contract),
2) a **deterministic Auto-Explainer** that maps structured orchestration events to schema-conformant explanations (plus short summaries),
3) an optional **viewer** for browsing episodes as an auditable timeline,
4) a small **scenario suite** (scripted event logs) and a **artifact-level validation + a study-pipeline demonstrator (synthetic responses)**.

---

## Why this exists

Self-healing improves robustness, but it can look *arbitrary* to humans if the system changes behavior without saying **why**. X-SHIELD is designed to make self-healing **understandable and governable** by producing explanations that are:

- **Faithful**: derived from recorded internal events + explicit mapping rules (not free-form generation).
- **Minimal but verifiable**: only a few high-signal evidence facts (typically 3–5), each traceable to event provenance.
- **Actionable**: states what changed and how success will be checked.
- **Auditable**: connects the episode to event IDs, agents, and versions.

---

## What this repo is (and is not)

### ✅ Included
- **X-SHIELD schema** (JSON Schema + design notes) for episode explanations.
- **Auto-Explainer** that:
  - parses JSONL event streams,
  - extracts episode boundaries (from trigger detection to post-check),
  - selects 3–5 evidence items,
  - generates:
    - a **schema-conformant explanation JSON**, and
    - a **two-level explanation**: teacher/operator summary + technical trace.
- **Scenario suite** of compact scripted logs covering *domain degradation* (e.g., repeated failure, uncertainty spikes) and *system degradation* (e.g., timeouts, invalid outputs, conflicts).
- **Viewer** (lightweight app) to inspect raw events and X-SHIELD episodes side-by-side.
- **Study pipeline scaffolding** for a future vignette-style user study (currently exercised with synthetic responses for workflow/plot generation).

### ❌ Not included (yet)
- A production deployment inside a real adaptive quiz platform.
- Human-participant study results (the repo currently contains artifact-level checks + synthetic study demonstrator outputs).
- About claim X-SHIELD improving learning outcomes; the focus here is explainability/governance of self-healing decisions.

---

## Repository layout (high level)

- `schema/` — X-SHIELD explanation contract (JSON Schema), design principles, examples  
- `explainer/` — deterministic Auto-Explainer (rules + templates)
- `data/scenarios/` — scripted JSONL orchestration logs (each contains one healing episode)
- `data/xshield_outputs/` — generated explanation JSON outputs
- `viewer/` — UI for browsing episodes (raw events vs X-SHIELD view)
- `scripts/` — utilities (e.g., schema validation helpers)
- `study/` — vignette-style study scaffolding + analysis/plot scripts (synthetic demo)

---

## Quickstart

### 1) Install
Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Generate X-SHIELD explanations from scenario logs
```bash
python explainer/explainer.py --in data/scenarios --out data/xshield_outputs
```

This reads `*.jsonl` event streams in `data/scenarios/` and writes schema-conformant explanations (e.g., `*_xshield.json`) into `data/xshield_outputs/`.

### 3) Run the viewer (optional)
A lightweight Streamlit viewer renders each scenario as an auditable episode timeline (raw events vs X-SHIELD view). See `viewer/` for the entrypoint and instructions.

### 4) Run the study pipeline (demo)
```bash
python3 study/make_demo_results.py --out study/results.csv --n_participants 8
python3 study/analyze.py --in study/results.csv --out paper/figures
```

### 5) One-command end-to-end
Optionally, helper scripts in `scripts/` can regenerate artifacts end-to-end.

### 6) (Optional) Validate schema compliance
This repo includes a validator script. Run it to ensure generated explanations conform to the schema:

```bash
python scripts/validate_schema.py
```

---

## What an X-SHIELD explanation contains
Each episode explanation is a single JSON object with fields organized around the explanation contract:
- **Context**: session/scenario identifiers and relevant metadata
- **Trigger**: what condition fired (and threshold/observed value when available)
- **Evidence (curated)**: 3–5 facts with provenance back to event IDs/types
- **Diagnosis (+ uncertainty)**: hypothesis and confidence when applicable
- **Recovery action**: selected action + parameters (e.g., fallback agent, prerequisite topic)
- **Expected effect + post-check**: what should improve and how it will be verified
- **Audit fields**: event IDs, agents involved, and version identifiers

It also includes a **two-level rendering**:
- a short **teacher/operator summary** (non-technical)
- a **technical trace** (precise signals/rule IDs/values)

---

## Viewer (optional)
The viewer presents, for each scenario:
- a baseline view of raw events
- an X-SHIELD view showing:
  - teacher summary,
  - curated evidence,
  - trigger/diagnosis/action/post-check fields,
  - audit references linked back to the same event stream.

See `viewer/` for how to run it (typically a Streamlit app).

---

## Status
This repository is a research prototype and artifact accompanying the paper:
“**X-SHIELD: Explainability-by-Design for Self-Healing Multi-Agent Orchestration in Adaptive Quizzes.**”

Current evidence in the repo is formative and artifact-level (schema validation, evidence compression, and deterministic generation on scripted scenarios). The `study/` directory is a reproducible analysis pipeline scaffold, currently demonstrated with synthetic responses to validate the workflow (not to claim human-study effects).

---

## Citation
If you use or build on this repository, please cite the paper in `paper/` (or the citation info provided alongside it).
