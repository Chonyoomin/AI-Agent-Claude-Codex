# Current Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode

## Sub-Phase
Phase 9F - Capacity-Halt Reprobe And Automatic Resume

## Status
Phase 9F is active as the next runtime-building slice under the approved Phase 9 autonomy contract. The goal is to extend the autonomous runtime across external-capacity interruptions with bounded retry, re-probe, and automatic-resume behavior while preserving the existing ownership boundary, artifact truth, review semantics, and halt/audit behavior.

## Task
Implement the Capacity-Halt Reprobe And Automatic Resume slice for the agent loop. This slice should treat Claude/Codex token or rate-limit exhaustion as a resumable external-capacity halt, persist bounded retry metadata beside the existing checkpoint, wait with bounded backoff, re-probe availability, and resume the exact suspended step automatically when capacity returns without silently widening autonomy or retrying forever, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Notes

- keep this slice narrow: implement capacity-halt re-probe and automatic resume only; do not broaden into final acceptance automation or unrelated runtime expansion yet
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep the new handoff layer aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human acceptance requirements
