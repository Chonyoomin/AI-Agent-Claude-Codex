# Current Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode

## Sub-Phase
Phase 9A - Autonomous Mode Contract And Safety Policy

## Status
Phase 9A is active as the first fully-autonomous-mode slice. The goal is to define the autonomy contract, safety policy, audit expectations, and hard-stop boundaries for a future selectable PRD-to-product mode without yet implementing the autonomous runtime itself.

## Task
Implement the Autonomous Mode Contract And Safety Policy slice for the agent loop. This slice should define what the future fully autonomous PRD-to-product mode is allowed to do, what still requires explicit human approval, how the mode remains auditable from repo artifacts, and which safety boundaries and hard stops are preserved, without yet implementing orchestrator-driven autonomous PRD execution.

## Notes

- keep this slice narrow: implement only the autonomy contract and safety policy; do not broaden into runtime execution yet
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- docs must distinguish shipped behavior from future roadmap behavior explicitly
- do not change the shipped `review`, `strict`, or `autonomous` semantics
- keep the contract aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human acceptance requirements
