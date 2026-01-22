# Scenario event logs (JSONL)

Each scenario is a **JSONL** file: one JSON object per line (no surrounding array).

## Minimum fields (every event)
- `event_id` (string): unique within a scenario (e.g., `e01`).
- `session_id` (string): scenario/session identifier (e.g., `s01`).
- `step` (int): monotonically increasing step index.
- `timestamp` (ISO 8601 string, UTC recommended): e.g., `2026-01-15T10:02:07Z`.
- `event_type` (string): enum-like, see below.
- `agent` (string): producing agent name (e.g., `monitor_agent`).
- `payload` (object): event-specific details.

## Required self-healing episode structure
Each scenario must contain at least one **healing episode** with the following sequence:

1. Normal activity events (e.g., `ANSWER_RECORDED`, `MONITOR_SIGNAL`).
2. `TRIGGER_DETECTED`
3. `DIAGNOSIS_SELECTED`
4. `RECOVERY_SELECTED`
5. `RECOVERY_EXECUTED`
6. `POST_CHECK`

**Note:** Some scenarios include multiple `RECOVERY_SELECTED` actions (e.g., retry then degraded mode).
The explainer will summarize the whole episode and choose the final recovery action before `POST_CHECK`,
while keeping the earlier actions in the technical trace/evidence.

## Event types used in this repo
### Learning/interaction
- `ANSWER_RECORDED`
  - payload keys (typical): `concept`, `difficulty`, `correct` (bool), optional `response_time_ms`
- `MONITOR_SIGNAL`
  - payload keys (typical): `signal_name`, `value`, optional `threshold`, optional `details`

### Self-healing control flow
- `TRIGGER_DETECTED`
  - payload keys: `trigger_type`, `rule_id`, optional `threshold`, optional `observed_value`
- `DIAGNOSIS_SELECTED`
  - payload keys: `hypothesis`, `confidence`, `rule_id`, optional `details`
- `RECOVERY_SELECTED`
  - payload keys: `action_type`, `parameters` (object), `rule_id`
- `RECOVERY_EXECUTED`
  - payload keys: `status` (`ok`/`fail`), optional `details`
- `POST_CHECK`
  - payload keys: `metric`, `value`, optional `details`

### Fault / system signals (may appear as evidence)
- `AGENT_TIMEOUT` (payload: `timeout_ms`, `agent_name`)
- `OUTPUT_INVALID` (payload: `validator`, `reason`, optional `agent_name`)
- `CONFLICTING_RECOMMENDATIONS` (payload: `recommendations` list, `conflict_score`)

## Naming convention
Scenario filename: `sXX_<short_name>_events.jsonl`

Example: `s04_agent_timeout_fallback_events.jsonl`
