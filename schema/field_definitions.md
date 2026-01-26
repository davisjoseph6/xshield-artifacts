# X-SHIELD Field Definitions (v0.1)

This document defines each field of the X-SHIELD explanation schema.

## Identification
- **schema_version**: Version of the schema (e.g., `"0.1"`)
- **episode_id**: Unique identifier of the self-healing episode
- **session_id**: Identifier of the learning session / scenario
- **timestamp_start**: Start time of the self-healing episode (ISO-8601)
- **timestamp_end**: End time of the self-healing episode (ISO-8601)

## Trigger
Describes why the self-healing mechanism started.

- **trigger_type**: Type of trigger (REPEATED_FAILURE, UNCERTAINTY_SPIKE, etc.)
- **threshold**: Threshold used by the rule (optional)
- **observed_value**: Observed metric value (optional)
- **trigger_rule_id**: Identifier of the rule that fired

## Evidence
List of **3 to 5** short facts supporting the trigger and diagnosis.

Each evidence item contains:
- **fact**: Short description of the observed fact
- **value**: Observed value
- **window**: Observation window (e.g., `last_5`, `t-30s..t`)
- **source_event_type**: Type of log event
- **source_event_ids**: Optional list of event identifiers

## Diagnosis
Hypothesis explaining the problem.

- **hypothesis**: One of MISCONCEPTION, DISENGAGEMENT, AMBIGUITY, SYSTEM_FAULT, DATA_QUALITY, UNKNOWN
- **confidence**: Confidence score between 0 and 1
- **diagnosis_rule_id**: Rule identifier used for diagnosis
- **alternatives**: Optional alternative hypotheses with confidence scores

## Recovery Action
Action selected by the orchestrator.

- **action_type**: One of PREREQUISITE_STEP, EASIER_ITEMS, DIAGNOSTIC_ITEM, HINT, FALLBACK_AGENT, RETRY, CIRCUIT_BREAK, DEGRADED_MODE
- **parameters**: Action-specific parameters
- **action_rule_id**: Rule identifier used to select the action

## Expected Effect
Defines how the system evaluates the success of recovery.

- **metric**: Metric to monitor
- **target_direction**: UP, DOWN or STABLE
- **check_after_steps**: Number of steps after which the metric is checked
- **success_criteria**: Optional human-readable success condition

## Explanation
Human-readable and technical explanations.

- **teacher_summary**: 2–3 sentence explanation for teachers (non-technical)
- **technical_trace**: Technical trace with rules and metrics
- **limitations**: Optional short description of uncertainty or limits

## Audit
Traceability and reproducibility information.

- **orchestrator**: Name and version of orchestrator
- **agents_involved**: List of agents contributing to the decision
- **source_event_range**: First and last event IDs used
- **hashes**: SHA-256 hash of log slice and explanation (hex)
- **notes**: Optional audit notes

