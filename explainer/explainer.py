#!/usr/bin/env python3
"""Auto-Explainer: scenario logs -> X-SHIELD explanations (schema-compliant).

Reads JSONL scenario event logs and generates:
- `*_xshield.json`: a structured explanation object (X-SHIELD schema, v0.1)
- `*_summary.txt`: a short teacher-facing summary (2–3 sentences)

High-level guarantees (evidence selection):
- Evidence is computed from a window around the trigger (k events before + rest of episode).
- Evidence is forced to include, when available:
  1) trigger-firing fact (TRIGGER_DETECTED payload),
  2) diagnosis-supporting fact (DIAGNOSIS_SELECTED payload),
  3) recovery action evidence (RECOVERY_SELECTED payload),
  4) post-check evidence (POST_CHECK payload) [optional but recommended].

CLI:
    python explainer/explainer.py --in data/scenarios --out data/xshield_outputs
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def find_last_before(
    events: List[Dict[str, Any]],
    end_idx: int,
    event_type: str
) -> Optional[Dict[str, Any]]:
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
    for ev in reversed(recovery_selected):
        params = ev.get("payload", {}).get("parameters", {})
        if isinstance(params, dict):
            if isinstance(params.get("n_items"), int):
                return max(1, params["n_items"])
            if isinstance(params.get("max_retries"), int):
                return max(1, params["max_retries"])
    return 2


def extract_context(
    events: List[Dict[str, Any]],
    slice_: EpisodeSlice,
    episode_events: List[Dict[str, Any]]
) -> Dict[str, Any]:
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


def _mk_event_fact(
    ev: Dict[str, Any],
    fact: str,
    window: str
) -> Dict[str, Any]:
    """Build a schema-compliant evidence item from a raw event."""
    return {
        "fact": fact,
        "value": ev.get("payload", {}),
        "window": window,
        "source_event_type": ev.get("event_type", "unknown"),
        "source_event_ids": [ev.get("event_id", "unknown")],
    }


def _add_unique_evidence(
    evidence: List[Dict[str, Any]],
    item: Dict[str, Any],
    seen_keys: set
) -> None:
    """Append evidence if it's not a duplicate (by (fact, source_event_ids))."""
    key = (item.get("fact"), tuple(item.get("source_event_ids", [])))
    if key in seen_keys:
        return
    evidence.append(item)
    seen_keys.add(key)


def _compute_answer_rollups(events: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    """Compute small, high-signal rollups from the last k ANSWER_RECORDED events."""
    answers = [e for e in events if e.get("event_type") == "ANSWER_RECORDED"]
    if not answers:
        return []

    lastk = answers[-k:]
    wrong = sum(1 for a in lastk if not a.get("payload", {}).get("correct", False))

    concept_counts: Dict[str, int] = {}
    for a in lastk:
        c = a.get("payload", {}).get("concept", "unknown")
        concept_counts[c] = concept_counts.get(c, 0) + (0 if a.get("payload", {}).get("correct", False) else 1)
    top_concept = max(concept_counts.items(), key=lambda kv: kv[1])[0]

    last_id = lastk[-1].get("event_id", "unknown")
    return [
        {
            "fact": f"Wrong answers in last {len(lastk)} items",
            "value": wrong,
            "window": f"last_{len(lastk)}",
            "source_event_type": "ANSWER_RECORDED",
            "source_event_ids": [last_id],
        },
        {
            "fact": f"Most frequent error concept in last {len(lastk)} items",
            "value": top_concept,
            "window": f"last_{len(lastk)}",
            "source_event_type": "ANSWER_RECORDED",
            "source_event_ids": [last_id],
        },
    ]


def _compute_signal_facts(events: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, Any]]:
    """Extract up to `limit` latest MONITOR_SIGNAL facts."""
    signals = [e for e in events if e.get("event_type") == "MONITOR_SIGNAL"]
    out: List[Dict[str, Any]] = []
    for sig in signals[-limit:]:
        payload = sig.get("payload", {})
        out.append({
            "fact": f"Monitor signal {payload.get('signal_name', 'unknown')}",
            "value": payload.get("value"),
            "window": payload.get("details", {}).get("window", "episode"),
            "source_event_type": "MONITOR_SIGNAL",
            "source_event_ids": [sig.get("event_id", "unknown")],
        })
    return out


def _compute_fault_facts(events: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, Any]]:
    """Extract up to `limit` latest system fault facts."""
    fault_types = ("AGENT_TIMEOUT", "OUTPUT_INVALID", "CONFLICTING_RECOMMENDATIONS")
    faults = [e for e in events if e.get("event_type") in fault_types]
    out: List[Dict[str, Any]] = []
    for fev in faults[-limit:]:
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

        out.append({
            "fact": fact,
            "value": val,
            "window": "episode",
            "source_event_type": fev.get("event_type"),
            "source_event_ids": [fev.get("event_id", "unknown")],
        })
    return out


def select_evidence(
    window_events: List[Dict[str, Any]],
    trigger_ev: Dict[str, Any],
    diagnosis_ev: Optional[Dict[str, Any]],
    recovery_evs: List[Dict[str, Any]],
    post_check_ev: Optional[Dict[str, Any]],
    max_items: int = 5
) -> List[Dict[str, Any]]:
    """Select 3–5 evidence facts (schema-compliant), guaranteed to include key episode anchors.

    Guarantees (if the corresponding event exists):
    - Trigger fact (TRIGGER_DETECTED) is included.
    - Diagnosis fact (DIAGNOSIS_SELECTED) is included.
    - Recovery action fact (last RECOVERY_SELECTED) is included.
    - Post-check fact (POST_CHECK) is included.
    """
    evidence: List[Dict[str, Any]] = []
    seen: set = set()

    # 1) Force required anchor facts first (so we never "trim them out").
    _add_unique_evidence(
        evidence,
        _mk_event_fact(trigger_ev, "Trigger detected", window="episode"),
        seen
    )

    if diagnosis_ev is not None:
        _add_unique_evidence(
            evidence,
            _mk_event_fact(diagnosis_ev, "Diagnosis selected", window="episode"),
            seen
        )

    if recovery_evs:
        # Prefer the final selected recovery (closest to what was executed).
        _add_unique_evidence(
            evidence,
            _mk_event_fact(recovery_evs[-1], "Recovery action selected", window="episode"),
            seen
        )

    if post_check_ev is not None:
        _add_unique_evidence(
            evidence,
            _mk_event_fact(post_check_ev, "Post-check performed", window="episode"),
            seen
        )

    # 2) Add compact supporting facts (rollups + latest signals/faults) until max_items.
    # These provide "why" context beyond the anchor event payloads.
    for item in _compute_answer_rollups(window_events, k=5):
        if len(evidence) >= max_items:
            break
        _add_unique_evidence(evidence, item, seen)

    for item in _compute_signal_facts(window_events, limit=2):
        if len(evidence) >= max_items:
            break
        _add_unique_evidence(evidence, item, seen)

    for item in _compute_fault_facts(window_events, limit=2):
        if len(evidence) >= max_items:
            break
        _add_unique_evidence(evidence, item, seen)

    # 3) Ensure minimum length (3) with lightweight fallbacks if needed.
    if len(evidence) < 3:
        for ev in window_events:
            et = ev.get("event_type")
            if et in ("TRIGGER_DETECTED", "DIAGNOSIS_SELECTED", "RECOVERY_SELECTED", "POST_CHECK"):
                item = _mk_event_fact(ev, f"Event {et}", window="episode")
                _add_unique_evidence(evidence, item, seen)
            if len(evidence) >= 3:
                break

    # 4) Trim (anchors already placed first).
    return evidence[:max_items]


def sha256_text(s: str) -> str:
    """Return SHA256 hex digest for a string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_xshield(
    scenario_path: Path,
    events: List[Dict[str, Any]],
    slice_: EpisodeSlice,
    episode_idx: int,
    *,
    evidence_pre_k: int = 5
) -> Dict[str, Any]:
    """Build a single X-SHIELD explanation object for one episode (schema compliant)."""
    episode_events = events[slice_.start_idx: slice_.end_idx + 1]
    session_id = episode_events[0].get("session_id", "unknown")
    episode_id = f"{session_id}_ep{episode_idx}"

    trigger_ev = episode_events[0]
    trigger_payload = trigger_ev.get("payload", {})

    trigger_type = trigger_payload.get("trigger_type") or "REPEATED_FAILURE"
    trigger_rule_id = trigger_payload.get("rule_id") or "T0"

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

    # Evidence window: k events before trigger + all events in the episode
    context_start = max(0, slice_.start_idx - max(0, int(evidence_pre_k)))
    window_events = events[context_start: slice_.end_idx + 1]

    evidence = select_evidence(
        window_events=window_events,
        trigger_ev=trigger_ev,
        diagnosis_ev=diagnosis_ev,
        recovery_evs=recovery_selected,
        post_check_ev=post_check_ev,
        max_items=5,
    )

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

    log_slice_text = json.dumps(window_events, ensure_ascii=False, sort_keys=True)
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
            "hashes": {
                "log_sha256": sha256_text(log_slice_text),
                "explanation_sha256": sha256_text(explanation_text),
            },
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
    parser.add_argument(
        "--evidence-pre-k",
        dest="evidence_pre_k",
        type=int,
        default=5,
        help="Number of events to include before TRIGGER_DETECTED when selecting evidence (default: 5)",
    )
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

        xshield = build_xshield(
            spath,
            events,
            episodes[0],
            episode_idx=1,
            evidence_pre_k=args.evidence_pre_k,
        )
        stem = spath.stem.replace("_events", "")
        write_outputs(out_dir, stem, xshield)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
