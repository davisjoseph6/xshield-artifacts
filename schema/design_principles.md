X-SHIELD Design Principles (v0.1)
Explainability-by-Design
Every self-healing decision must produce a structured explanation.

Minimal but Sufficient
Evidence is limited to 3–5 facts. Enums are small and stable.

Two-Level Explanation

Teacher summary: non-technical, short, actionable
Technical trace: references rules and metrics for reproducibility
Traceability
Each explanation must reference:
Trigger, diagnosis and action rule IDs
Event ranges and agent names
Auditability
Explanations must allow reconstruction of the decision process using logs and hashes.

Generator-Friendly
The schema must remain simple and stable to support automatic generation.

Human Actionability
Each recovery action must specify an expected effect and when to evaluate it.
