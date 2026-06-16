# Current Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode

## Sub-Phase
Phase 9B - PRD Intake And Decomposition

## Status
Phase 9B is active as the first runtime-building slice under the approved Phase 9A contract. The goal is to accept a structured PRD or looser product brief, normalize it into a canonical intake/decomposition surface, and derive bounded internal phases, tasks, risks, and acceptance criteria without yet automating prompt handoff or cross-phase autonomous execution.

## Task
Implement the PRD Intake And Decomposition slice for the agent loop. This slice should accept a structured PRD or looser product brief, normalize it into a canonical autonomous-run intake surface, and decompose it into bounded internal phases, tasks, risks, and acceptance criteria while preserving the existing planner, activation, approval, and artifact-truth boundaries.

## Notes

- keep this slice narrow: implement only PRD intake and bounded decomposition; do not broaden into prompt handoff, autonomous review/fix execution, automatic phase activation, or final-run completion logic yet
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any intake/decomposition output must stay bounded, reviewable, and compatible with the shipped phase/task model rather than inventing a parallel control plane
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep the new intake/decomposition layer aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human acceptance requirements
