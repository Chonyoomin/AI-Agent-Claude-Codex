# Current Task

## Phase
Phase 8 - Documentation and Project Polish

## Sub-Phase
Phase 8A - Architecture And Usage Docs

## Status
Phase 8A is active as the first documentation/polish slice. The goal is to explain the real shipped loop, runtime surfaces, and operator workflow from a clean clone while preserving the shipped runtime semantics and avoiding any documentation drift that invents unshipped behavior.

## Task
Implement the Architecture And Usage Docs slice for the agent loop. This slice should document the real shipped workflow from a clean clone, including the end-to-end loop, active CLI/runtime surfaces, artifact ownership model, and practical operator flows, while preserving the current runtime behavior and avoiding any documentation that promises unshipped automation, hidden capabilities, or alternate sources of truth.

## Notes

- keep this slice narrow: implement only architecture and usage documentation; do not broaden into new runtime or UI features
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- docs must distinguish shipped behavior from future roadmap behavior explicitly
- do not change the shipped `review`, `strict`, or `autonomous` semantics
