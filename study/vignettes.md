# Vignettes for X-SHIELD Study

This document contains short vignettes shown to participants.
For each scenario, we provide:
- A **baseline** vignette (less structured, human-readable, minimal fields).
- An **X-SHIELD** vignette (fully structured JSON that conforms to `schema/xshield_schema.json`).

> Note: Scenario labels like “random guessing” are expressed in the schema via the closest stable diagnosis
> (e.g., DISENGAGEMENT) and/or via evidence/summary, because X-SHIELD intentionally keeps enums small.

---

## Scenario s02_random_guessing

**Context:** The system detected behavior consistent with random guessing / low engagement.

### Baseline condition (unstructured)
```json
{
  "trigger_type": "UNCERTAINTY_SPIKE",
  "evidence": [
    "Very fast responses across recent items",
    "Uncertainty/instability increased sharply"
  ],
  "diagnosis_hypothesis": "DISENGAGEMENT",
  "recovery_action_type": "EASIER_ITEMS",
  "expected_effect": "Increase engagement and correctness over the next few questions"
}
```

### X-SHIELD condition (schema-aligned)

```json
{
  "schema_version": "0.1",
  "episode_id": "s02_ep1",
  "session_id": "s02",
  "timestamp_start": "2026-01-22T10:05:02Z",
  "timestamp_end": "2026-01-22T10:05:10Z",
  "trigger": {
    "trigger_type": "UNCERTAINTY_SPIKE",
    "trigger_rule_id": "T2",
    "observed_value": 0.82,
    "threshold": 0.75
  },
  "evidence": [
    {
      "fact": "Very fast responses",
      "value": "≈1.2s median",
      "window": "last_5",
      "source_event_type": "ANSWER_RECORDED",
      "source_event_ids": ["e29", "e31", "e33", "e35", "e37"]
    },
    {
      "fact": "High uncertainty",
      "value": 0.82,
      "window": "last_5",
      "source_event_type": "MONITOR_SIGNAL",
      "source_event_ids": ["e30", "e32", "e34", "e36", "e38"]
    },
    {
      "fact": "Guess-rate elevated",
      "value": 0.60,
      "window": "last_5",
      "source_event_type": "MONITOR_SIGNAL",
      "source_event_ids": ["e30", "e32", "e34", "e36", "e38"]
    }
  ],
  "diagnosis": {
    "hypothesis": "DISENGAGEMENT",
    "confidence": 0.65,
    "diagnosis_rule_id": "D3",
    "alternatives": [
      { "hypothesis": "AMBIGUITY", "confidence": 0.22 }
    ]
  },
  "recovery_action": {
    "action_type": "EASIER_ITEMS",
    "parameters": { "difficulty_shift": -1, "n_items": 3 },
    "action_rule_id": "R2"
  },
  "expected_effect": {
    "metric": "engagement_score",
    "target_direction": "UP",
    "check_after_steps": 3,
    "success_criteria": "Engagement score increases after 3 items and uncertainty decreases"
  },
  "explanation": {
    "teacher_summary": "The system detected signs of random guessing/low engagement (very fast responses and high uncertainty). It temporarily switched to easier questions to restore confidence and engagement.",
    "technical_trace": "Trigger T2 (uncertainty 0.82 > 0.75). Diagnosis D3: DISENGAGEMENT (0.65). Action R2: EASIER_ITEMS (n_items=3, shift=-1).",
    "limitations": "Signals may also match ambiguity; results are checked after the next 3 items."
  },
  "audit": {
    "orchestrator": { "name": "SelfHealingOrchestrator", "version": "0.1" },
    "agents_involved": [
      { "agent_name": "MonitorAgent", "agent_role": "monitoring", "agent_version": "0.1" }
    ],
    "source_event_range": { "first_event_id": "e29", "last_event_id": "e38" },
    "hashes": {
      "log_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "explanation_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    },
    "notes": "Vignette JSON uses stable enums; random-guessing expressed via evidence + summary."
  }
}
```

## Scenario s04_invalid_output_data_quality

Context: An agent produced an invalid structured output. The system escalated to degraded mode.

### Baseline condition (unstructured)

```json
{
  "trigger_type": "OUTPUT_INVALID",
  "evidence": [
    "Invalid JSON output detected by validator",
    "Missing required fields in the agent output"
  ],
  "diagnosis_hypothesis": "DATA_QUALITY",
  "recovery_action_type": "DEGRADED_MODE",
  "expected_effect": "Increase output validation pass rate immediately"
}
```

### X-SHIELD condition (schema-aligned)

```json
{
  "schema_version": "0.1",
  "episode_id": "s04_ep1",
  "session_id": "s04",
  "timestamp_start": "2026-01-22T10:20:08Z",
  "timestamp_end": "2026-01-22T10:20:30Z",
  "trigger": {
    "trigger_type": "OUTPUT_INVALID",
    "trigger_rule_id": "T6",
    "observed_value": "missing required field",
    "threshold": "schema-valid JSON"
  },
  "evidence": [
    {
      "fact": "Invalid JSON output",
      "value": "missing field",
      "window": "t-2s..t",
      "source_event_type": "OUTPUT_VALIDATION_FAILED",
      "source_event_ids": ["e66"]
    },
    {
      "fact": "Repeated validation failures",
      "value": 2,
      "window": "t-10s..t",
      "source_event_type": "OUTPUT_VALIDATION_FAILED",
      "source_event_ids": ["e65", "e66"]
    },
    {
      "fact": "Upstream data flagged as low-quality",
      "value": true,
      "window": "t-10s..t",
      "source_event_type": "MONITOR_SIGNAL",
      "source_event_ids": ["e64"]
    }
  ],
  "diagnosis": {
    "hypothesis": "DATA_QUALITY",
    "confidence": 0.70,
    "diagnosis_rule_id": "D7"
  },
  "recovery_action": {
    "action_type": "DEGRADED_MODE",
    "parameters": {
      "reason": "validation_failed_after_retry",
      "previous_action": "RETRY",
      "max_retries": 1,
      "agent": "ItemSelectionAgent"
    },
    "action_rule_id": "R7"
  },
  "expected_effect": {
    "metric": "output_validation_pass_rate",
    "target_direction": "UP",
    "check_after_steps": 1,
    "success_criteria": "Next output passes validation"
  },
  "explanation": {
    "teacher_summary": "The system detected an invalid output (missing fields) and signs of low-quality input data. It switched to degraded mode to produce a safe, schema-valid output path.",
    "technical_trace": "Trigger T6 fired (OUTPUT_INVALID). Diagnosis D7: DATA_QUALITY (0.70). Action R7: DEGRADED_MODE (after RETRY max_retries=1).",
    "limitations": "Degraded mode prioritizes validity/safety over optimal personalization."
  },
  "audit": {
    "orchestrator": { "name": "SelfHealingOrchestrator", "version": "0.1" },
    "agents_involved": [
      { "agent_name": "RecoveryAgent", "agent_role": "recovery", "agent_version": "0.1" }
    ],
    "source_event_range": { "first_event_id": "e64", "last_event_id": "e71" },
    "hashes": {
      "log_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "explanation_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    }
  }
}
```

---

