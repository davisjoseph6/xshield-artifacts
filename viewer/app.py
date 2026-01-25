#!/usr/bin/env python3
"""Streamlit viewer for X-SHIELD: Baseline logs vs X-SHIELD explanations."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SCEN_DIR = ROOT / "data" / "scenarios"
OUT_DIR = ROOT / "data" / "xshield_outputs"


def read_jsonl(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        events.append(json.loads(line))
    return events


def payload_preview(payload: dict, max_keys: int = 6) -> str:
    if not isinstance(payload, dict):
        return ""
    keys = list(payload.keys())[:max_keys]
    small = {k: payload.get(k) for k in keys}
    return json.dumps(small, ensure_ascii=False)


st.set_page_config(page_title="X-SHIELD Viewer", layout="wide")
st.title("X-SHIELD Viewer")

scenario_files = sorted(SCEN_DIR.glob("s*_events.jsonl"))
if not scenario_files:
    st.error(f"No scenarios found in {SCEN_DIR}")
    st.stop()

choices = [p.name for p in scenario_files]
choice = st.selectbox("Select a scenario (baseline log)", choices)

show_baseline = st.checkbox("Show baseline (event log)", value=True)
show_xshield = st.checkbox("Show X-SHIELD explanation", value=True)

scenario_path = SCEN_DIR / choice
stem = scenario_path.stem.replace("_events", "")
xshield_path = OUT_DIR / f"{stem}_xshield.json"

events = read_jsonl(scenario_path)

if show_xshield:
    st.subheader("X-SHIELD explanation")
    if not xshield_path.exists():
        st.error(f"Missing generated explanation: {xshield_path.name}. Run: `bash scripts/regen.sh`")
    else:
        x = json.loads(xshield_path.read_text(encoding="utf-8"))

        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown("**Teacher summary**")
            st.write(x["explanation"]["teacher_summary"])
            st.markdown("**Technical trace**")
            st.write(x["explanation"]["technical_trace"])

        with col2:
            st.markdown("**Trigger**")
            st.json(x["trigger"])
            st.markdown("**Diagnosis**")
            st.json(x["diagnosis"])
            st.markdown("**Recovery action**")
            st.json(x["recovery_action"])
            st.markdown("**Expected effect**")
            st.json(x["expected_effect"])

        st.markdown("**Evidence (3–5 facts)**")
        for ev in x["evidence"]:
            st.write(f"- **{ev['fact']}** → {ev['value']}  _(window={ev['window']}, source={ev['source_event_type']})_")

if show_baseline:
    st.subheader("Baseline: event log")
    rows = []
    for e in events:
        rows.append({
            "step": e.get("step"),
            "timestamp": e.get("timestamp"),
            "event_type": e.get("event_type"),
            "agent": e.get("agent"),
            "payload_preview": payload_preview(e.get("payload", {})),
        })
    df = pd.DataFrame(rows).sort_values("step")
    st.dataframe(df, width="stretch")

    with st.expander("Raw JSONL (parsed)"):
        st.json(events)

