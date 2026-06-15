# Current Task

## Phase
Phase 8 - Documentation and Project Polish

## Sub-Phase
Phase 8C - Final README Alignment And Clean-Clone Polish

## Status
Phase 8C is active as the final documentation/polish slice. The goal is to make the README, examples, and clean-clone getting-started path line up exactly with the shipped behavior and the already-delivered Phase 8A/8B docs without changing runtime behavior or inventing unshipped automation.

## Task
Implement the Final README Alignment And Clean-Clone Polish slice for the agent loop. This slice should ensure the README, examples, and getting-started path match the shipped CLI/runtime behavior, current artifact ownership model, and future-roadmap boundaries exactly, while preserving the current runtime behavior and avoiding any documentation that promises unshipped automation, hidden capabilities, or alternate sources of truth.

## Notes

- keep this slice narrow: implement only final README alignment and clean-clone polish; do not broaden into new runtime or UI features
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- docs must distinguish shipped behavior from future roadmap behavior explicitly
- do not change the shipped `review`, `strict`, or `autonomous` semantics
- keep README and getting-started guidance aligned with the shipped halt/refusal vocabulary, the current CLI-first operator flow, and the Phase 8A/8B operator docs
