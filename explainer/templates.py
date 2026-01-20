#!/usr/bin/env python3
"""X-SHIELD teacher-summary templates.

This module centralizes short, non-technical summaries that are shown to teachers/auditors.
Templates are keyed by (trigger_type, hypothesis, action_type).

Keep these templates short (2–3 sentences). Avoid jargon.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


TemplateKey = Tuple[str, str, str]


TEMPLATES: Dict[TemplateKey, str] = {
    ("REPEATED_FAILURE", "MISCONCEPTION", "PREREQUISITE_STEP"):
        "The system detected repeated errors on {concept} (above the allowed threshold). "
        "It switched to a short prerequisite check on {prereq_concept} for {n_items} question(s), "
        "then will reassess performance.",

    ("UNCERTAINTY_SPIKE", "DISENGAGEMENT", "EASIER_ITEMS"):
        "The system detected signs of guessing/low engagement on {concept}. "
        "It temporarily switched to easier items ({n_items} question(s)) to re-stabilize performance and attention.",

    ("UNCERTAINTY_SPIKE", "AMBIGUITY", "DIAGNOSTIC_ITEM"):
        "The system detected high uncertainty on {concept}. "
        "It asked a short diagnostic question to clarify what the student knows, then will adjust the next steps.",

    ("AGENT_TIMEOUT", "SYSTEM_FAULT", "FALLBACK_AGENT"):
        "A support agent did not respond in time, so the system switched to a backup agent to keep the session running. "
        "It will monitor whether timeouts stop after the switch.",

    ("OUTPUT_INVALID", "DATA_QUALITY", "DEGRADED_MODE"):
        "The system detected invalid generated content. It first retried, then switched to a safer degraded mode "
        "to keep the session consistent while reducing the risk of further invalid outputs.",

    ("CONFLICTING_RECOMMENDATIONS", "UNKNOWN", "CIRCUIT_BREAK"):
        "Multiple agents recommended different actions at the same time. "
        "The system applied an arbitration rule to choose a safe next step, then will monitor if conflicts reduce.",

    ("INCONSISTENCY", "DISENGAGEMENT", "HINT"):
        "The system detected little learning progress over several steps. "
        "It provided a guided hint to help the student unblock, then will re-check progress.",

    ("UNCERTAINTY_SPIKE", "DATA_QUALITY", "DIAGNOSTIC_ITEM"):
        "The system detected noisy/unstable signals. "
        "It ran a short confirmatory check to verify the situation before changing the learning path.",
}


def render_teacher_summary(
    trigger_type: str,
    hypothesis: str,
    action_type: str,
    context: Dict[str, Any],
) -> str:
    """Render a 2–3 sentence teacher-facing summary.

    Args:
        trigger_type: The self-healing trigger type.
        hypothesis: Diagnosis hypothesis.
        action_type: Recovery action type.
        context: Key-value context used to fill templates.

    Returns:
        A concise human-readable summary.
    """
    key = (trigger_type, hypothesis, action_type)
    template = TEMPLATES.get(key)
    if template is None:
        # Generic fallback: still human-readable and audit-friendly.
        return (
            "The system detected a problem during the session and started a self-healing step. "
            f"It diagnosed the situation as {hypothesis.lower().replace('_', ' ')} and applied "
            f"the action {action_type.lower().replace('_', ' ')}. "
            "It will check whether the monitored metric improves after the intervention."
        )

    # Fill with safe defaults to avoid KeyError if a scenario omits some context.
    safe_context = {
        "concept": context.get("concept", "the current topic"),
        "prereq_concept": context.get("prereq_concept", "a prerequisite topic"),
        "n_items": context.get("n_items", context.get("check_after_steps", 2)),
    }
    safe_context.update(context)
    return template.format(**safe_context)
