# Current Task

## Phase
Phase 8 - Documentation and Project Polish

## Sub-Phase
Phase 8B - Safety, Approval, And Operational Playbooks

## Status
Phase 8B is active as the second documentation/polish slice. The goal is to document the shipped safety model, approval semantics, halt and recovery guidance, and operator troubleshooting playbooks without changing runtime behavior or inventing unshipped automation.

## Task
Implement the Safety, Approval, And Operational Playbooks slice for the agent loop. This slice should document the shipped halt reasons, approval modes, recovery paths, and troubleshooting guidance in operator-facing playbooks while preserving the current runtime behavior and avoiding any documentation that promises unshipped automation, hidden capabilities, or alternate sources of truth.

## Notes

- keep this slice narrow: implement only safety, approval, recovery, and troubleshooting playbooks; do not broaden into new runtime or UI features
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- docs must distinguish shipped behavior from future roadmap behavior explicitly
- do not change the shipped `review`, `strict`, or `autonomous` semantics
- keep the new playbooks aligned with the shipped halt/refusal vocabulary and the existing CLI-first operator flow
