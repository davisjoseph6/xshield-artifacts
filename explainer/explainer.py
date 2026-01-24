#!/usr/bin/env python3
"""Auto-Explainer: scenario logs -> X-SHIELD explanations (schema-compliant).

Reads JSONL scenario event logs and generates:
- `*_xshield.json`: a structured explanation object (X-SHIELD schema, v0.1)
- `*_summary.txt`: a short teacher-facing summary (2–3 sentences)

CLI:
    python explainer/explainer.py --in data/scenarios --out data/xshield_outputs
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from templates import render_teacher_summary


@dataclass(frozen=True)
class EpisodeSlice:
    """A contiguous slice of events representing one self-healing episode."""
    start_idx: int
    end_idx: int  # inclusive


ROLE_MAP: Dict[str, str] = {
    "monitor_agent": "monitoring",
    "diagnose_agent": "diagnosis",
    "recovery_agent": "recovery",
    "feedback_agent": "feedback",
    "question_generator_agent": "generation",
    "orchestrator": "orchestration",
}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of event dicts."""
    events: List[Dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        events.append(json.loads(line))
    return events


def find_last_before(events: List[Dict[str, Any]], end_idx: int, event_type: str) -> Optional[Dict[str, Any]]:
    """Return last event of type `event_type` at or before `end_idx`."""
    for i in range(end_idx, -1, -1):
        if events[i].get("event_type") == event_type:
            return events[i]
    return None


def slice_episodes(events: List[Dict[str, Any]]) -> List[EpisodeSlice]:
    """Find self-healing episodes, starting at TRIGGER_DETECTED and ending at POST_CHECK."""
    slices: List[EpisodeSlice] = []
    i = 0
    while i < len(events):
        if events[i].get("event_type") != "TRIGGER_DETECTED":
            i += 1
            continue

        start = i
        end = i
        for j in range(i, len(events)):
            end = j
            if events[j].get("event_type") == "POST_CHECK":
                break

        slices.append(EpisodeSlice(start_idx=start, end_idx=end))
        i = end + 1
    return slices


def infer_target_direction(metric: str) -> str:
    """Heuristic: infer whether metric should go UP or DOWN."""
    m = (metric or "").lower()
    down_markers = ("error", "uncertainty", "timeout", "latency", "invalid", "conflict", "noise", "rate")
    if any(k in m for k in down_markers):
        return "DOWN"
    return "UP"


def compute_check_after_steps(recovery_selected: List[Dict[str, Any]]) -> int:
    """Compute check_after_steps from the most recent recovery params that specify pacing."""
    # Look from the last selected action backwards, until we find n_items or max_retries.
    for ev in reversed(recovery_selected):
        params = ev.get("payload", {}).get("parameters", {})
        if isinstance(params, dict):
            if isinstance(params.get("n_items"), int):
                return max(1, params["n_items"])
            if isinstance(params.get("max_retries"), int):
                return max(1, params["max_retries"])
    return 2


def extract_context(events: List[Dict[str, Any]], slice_: EpisodeSlice, episode_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract lightweight context for templating (concepts, counts)."""
    context: Dict[str, Any] = {}

    # Prefer the last concept BEFORE the trigger (more faithful to what caused healing).
    for ev in reversed(events[: slice_.start_idx]):
        if ev.get("event_type") == "ANSWER_RECORDED":
            concept = ev.get("payload", {}).get("concept")
            if concept:
                context["concept"] = concept
                break

    # Fallback: last concept within episode
    if "concept" not in context:
        for ev in reversed(episode_events):
            if ev.get("event_type") == "ANSWER_RECORDED":
                concept = ev.get("payload", {}).get("concept")
                if concept:
                    context["concept"] = concept
                    break

    # Pull action params for templates
    for ev in episode_events:
        if ev.get("event_type") == "RECOVERY_SELECTED":
            payload = ev.get("payload", {})
            params = payload.get("parameters", {}) if isinstance(payload.get("parameters", {}), dict) else {}

            if payload.get("action_type") == "PREREQUISITE_STEP":
                if "concept" in params:
                    context["prereq_concept"] = params["concept"]
                if "n_items" in params:
                    context["n_items"] = params["n_items"]

            if payload.get("action_type") == "EASIER_ITEMS":
                if "n_items" in params:
                    context["n_items"] = params["n_items"]

            if payload.get("action_type") == "DIAGNOSTIC_ITEM":
                if "n_items" in params:
                    context["n_items"] = params["n_items"]

    return context


def select_evidence(episode_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Select 3–5 evidence facts (schema-compliant evidence items)."""
    evidence: List[Dict[str, Any]] = []

    answers = [e for e in episode_events if e.get("event_type") == "ANSWER_RECORDED"]
    signals = [e for e in episode_events if e.get("event_type") == "MONITOR_SIGNAL"]
    faults = [e for e in episode_events if e.get("event_type") in ("AGENT_TIMEOUT", "OUTPUT_INVALID", "CONFLICTING_RECOMMENDATIONS")]

    if answers:
        last5 = answers[-5:]
        wrong = sum(1 for a in last5 if not a.get("payload", {}).get("correct", False))
        concept_counts: Dict[str, int] = {}
        for a in last5:
            c = a.get("payload", {}).get("concept", "unknown")
            concept_counts[c] = concept_counts.get(c, 0) + (0 if a.get("payload", {}).get("correct", False) else 1)
        top_concept = max(concept_counts.items(), key=lambda kv: kv[1])[0]

        evidence.append({
            "fact": "Wrong answers in last 5 items",
            "value": wrong,
            "window": "last_5",
            "source_event_type": "ANSWER_RECORDED",
            "source_event_ids": [last5[-1].get("event_id", "unknown")],
        })
        evidence.append({
            "fact": "Most frequent error concept in last 5 items",
            "value": top_concept,
            "window": "last_5",
            "source_event_type": "ANSWER_RECORDED",
            "source_event_ids": [last5[-1].get("event_id", "unknown")],
        })

    for sig in signals[-2:]:
        payload = sig.get("payload", {})
        evidence.append({
            "fact": f"Monitor signal {payload.get('signal_name', 'unknown')}",
            "value": payload.get("value"),
            "window": payload.get("details", {}).get("window", "episode"),
            "source_event_type": "MONITOR_SIGNAL",
            "source_event_ids": [sig.get("event_id", "unknown")],
        })

    for fev in faults[-2:]:
        payload = fev.get("payload", {})
        if fev.get("event_type") == "AGENT_TIMEOUT":
            fact = "Agent timeout"
            val = f"{payload.get('agent_name', 'unknown')} ({payload.get('timeout_ms', 'unknown')}ms)"
        elif fev.get("event_type") == "OUTPUT_INVALID":
            fact = "Invalid output detected"
            val = payload.get("reason", "unknown")
        else:
            fact = "Conflicting recommendations"
            val = payload.get("conflict_score", "unknown")

        evidence.append({
            "fact": fact,
            "value": val,
            "window": "episode",
            "source_event_type": fev.get("event_type"),
            "source_event_ids": [fev.get("event_id", "unknown")],
        })

    evidence = evidence[:5]

    # Ensure at least 3
    if len(evidence) < 3:
        for ev in episode_events:
            if ev.get("event_type") in ("TRIGGER_DETECTED", "DIAGNOSIS_SELECTED", "RECOVERY_SELECTED"):
                evidence.append({
                    "fact": f"Event {ev.get('event_type')}",
                    "value": ev.get("payload", {}),
                    "window": "episode",
                    "source_event_type": ev.get("event_type"),
                    "source_event_ids": [ev.get("event_id", "unknown")],
                })
            if len(evidence) >= 3:
                break

    return evidence[:5]


def sha256_text(s: str) -> str:
    """Return SHA256 hex digest for a string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_xshield(scenario_path: Path, events: List[Dict[str, Any]], slice_: EpisodeSlice, episode_idx: int) -> Dict[str, Any]:
    """Build a single X-SHIELD explanation object for one episode (schema compliant)."""
    episode_events = events[slice_.start_idx: slice_.end_idx + 1]
    session_id = episode_events[0].get("session_id", "unknown")
    episode_id = f"{session_id}_ep{episode_idx}"

    trigger_ev = episode_events[0]
    trigger_payload = trigger_ev.get("payload", {})

    trigger_type = trigger_payload.get("trigger_type")
    trigger_rule_id = trigger_payload.get("rule_id")
    if not trigger_type:
        trigger_type = "REPEATED_FAILURE"
    if not trigger_rule_id:
        trigger_rule_id = "T0"

    last_signal = find_last_before(events, slice_.start_idx, "MONITOR_SIGNAL")
    if last_signal is not None:
        sig_payload = last_signal.get("payload", {})
        threshold = trigger_payload.get("threshold", sig_payload.get("threshold"))
        observed_value = trigger_payload.get("observed_value", sig_payload.get("value"))
    else:
        threshold = trigger_payload.get("threshold")
        observed_value = trigger_payload.get("observed_value")

    diagnosis_ev = next((e for e in episode_events if e.get("event_type") == "DIAGNOSIS_SELECTED"), None)
    diagnosis_payload = (diagnosis_ev or {}).get("payload", {})
    hypothesis = diagnosis_payload.get("hypothesis") or "UNKNOWN"
    diagnosis_rule_id = diagnosis_payload.get("rule_id") or "D0"
    diag_conf_raw = diagnosis_payload.get("confidence")
    diag_conf = float(diag_conf_raw) if isinstance(diag_conf_raw, (int, float)) else 0.5

    recovery_selected = [e for e in episode_events if e.get("event_type") == "RECOVERY_SELECTED"]
    action_ev = recovery_selected[-1] if recovery_selected else None
    action_payload = (action_ev or {}).get("payload", {})

    action_type = action_payload.get("action_type") or "RETRY"
    action_params = action_payload.get("parameters", {})
    if not isinstance(action_params, dict):
        action_params = {}
    action_rule_id = action_payload.get("rule_id") or "R0"

    post_check_ev = next((e for e in reversed(episode_events) if e.get("event_type") == "POST_CHECK"), None)
    post_payload = (post_check_ev or {}).get("payload", {})
    metric = post_payload.get("metric", "unknown_metric")

    check_after_steps = compute_check_after_steps(recovery_selected)

    # Evidence: include small context before trigger so evidence matches cause
    context_start = max(0, slice_.start_idx - 5)
    context_events = events[context_start: slice_.end_idx + 1]
    evidence = select_evidence(context_events)

    context = extract_context(events, slice_, episode_events)
    context["check_after_steps"] = check_after_steps

    teacher_summary = render_teacher_summary(trigger_type, hypothesis, action_type, context)

    actions_trace = []
    for r in recovery_selected:
        rp = r.get("payload", {})
        actions_trace.append(f"{rp.get('rule_id', 'R0')}: {rp.get('action_type')}({rp.get('parameters', {})})")
    actions_str = " -> ".join(actions_trace) if actions_trace else f"{action_rule_id}: {action_type}({action_params})"

    technical_trace = (
        f"Trigger {trigger_rule_id} fired: {trigger_type} observed={observed_value} threshold={threshold}. "
        f"Diagnosis {diagnosis_rule_id}: {hypothesis} ({diag_conf}). "
        f"Actions: {actions_str}. "
        f"Post-check: {metric}={post_payload.get('value')}."
    )

    # Schema-compliant audit
    agents = sorted({e.get("agent", "unknown") for e in episode_events})
    agents_involved = []
    for a in agents:
        agents_involved.append({
            "agent_name": a,
            "agent_role": ROLE_MAP.get(a, "unknown"),
            "agent_version": None,
        })

    first_event_id = trigger_ev.get("event_id", "unknown")
    last_event_id = (post_check_ev or episode_events[-1]).get("event_id", "unknown")

    log_slice_text = json.dumps(context_events, ensure_ascii=False, sort_keys=True)
    explanation_text = json.dumps(
        {"teacher_summary": teacher_summary, "technical_trace": technical_trace},
        ensure_ascii=False,
        sort_keys=True,
    )

    xshield: Dict[str, Any] = {
        "schema_version": "0.1",
        "episode_id": episode_id,
        "session_id": session_id,
        "timestamp_start": trigger_ev.get("timestamp"),
        "timestamp_end": (post_check_ev or trigger_ev).get("timestamp"),
        "trigger": {
            "trigger_type": trigger_type,
            "threshold": threshold,
            "observed_value": observed_value,
            "trigger_rule_id": trigger_rule_id,
        },
        "evidence": evidence,
        "diagnosis": {
            "hypothesis": hypothesis,
            "confidence": diag_conf,
            "diagnosis_rule_id": diagnosis_rule_id,
        },
        "recovery_action": {
            "action_type": action_type,
            "parameters": action_params,
            "action_rule_id": action_rule_id,
        },
        "expected_effect": {
            "metric": metric,
            "target_direction": infer_target_direction(metric),
            "check_after_steps": check_after_steps,
        },
        "explanation": {
            "teacher_summary": teacher_summary,
            "technical_trace": technical_trace,
        },
        "audit": {
            "orchestrator": {"name": "SelfHealingOrchestrator", "version": "0.1"},
            "agents_involved": agents_involved,
            "source_event_range": {"first_event_id": first_event_id, "last_event_id": last_event_id},
            "hashes": {"log_sha256": sha256_text(log_slice_text), "explanation_sha256": sha256_text(explanation_text)},
            "notes": f"scenario_file={scenario_path.name}",
        },
    }
    return xshield


def write_outputs(out_dir: Path, stem: str, xshield: Dict[str, Any]) -> None:
    """Write JSON + summary outputs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}_xshield.json"
    txt_path = out_dir / f"{stem}_summary.txt"

    json_path.write_text(json.dumps(xshield, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    txt_path.write_text(xshield.get("explanation", {}).get("teacher_summary", "") + "\n", encoding="utf-8")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate X-SHIELD explanations from JSONL scenarios.")
    parser.add_argument("--in", dest="in_dir", required=True, help="Input directory with *.jsonl scenarios")
    parser.add_argument("--out", dest="out_dir", required=True, help="Output directory for xshield outputs")
    args = parser.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)

    scenario_files = sorted(in_dir.glob("*.jsonl"))
    if not scenario_files:
        raise SystemExit(f"No scenario files found in {in_dir}")

    for spath in scenario_files:
        events = read_jsonl(spath)
        episodes = slice_episodes(events)
        if not episodes:
            continue
        xshield = build_xshield(spath, events, episodes[0], episode_idx=1)
        stem = spath.stem.replace("_events", "")
        write_outputs(out_dir, stem, xshield)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

