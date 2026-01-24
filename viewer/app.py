import streamlit as st
import json

scenarios = ["s01_repeated_failure.json", "s02_random_guessing.json", "s03_uncertainty_spike.json", "s04_agent_timeout.json"]
scenario_choice = st.selectbox("Select a scenario", scenarios)

file_path = f"data/xshield_outputs/{scenario_choice}"
with open(file_path) as f:
    data = json.load(f)

st.subheader("Teacher-friendly explanation")
st.write(data["teacher_summary"])

st.subheader("Technical explanation (JSON)")
st.json(data)
