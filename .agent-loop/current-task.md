# Current Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode

## Sub-Phase
Phase 9C - Orchestrator-Driven Prompt Handoff

## Status
Phase 9C is active as the next runtime-building slice under the approved Phase 9 autonomy contract. The goal is to remove manual prompt transfer by letting the orchestrator drive Codex/Claude prompt handoff from canonical repo artifacts while preserving the existing ownership boundary, review semantics, and halt/audit behavior.

## Task
Implement the Orchestrator-Driven Prompt Handoff slice for the agent loop. This slice should let the orchestrator dispatch the active Codex/Claude prompt handoff from canonical prompt artifacts and capture the resulting handoff audit trail without requiring manual copy/paste, while preserving the shipped planner/activation boundary, review ownership model, and per-phase human gate.

## Notes

- keep this slice narrow: implement prompt handoff only; do not broaden into autonomous review/fix continuation, automatic next-phase activation, long-run completion heuristics, capacity re-probe, or final-run completion logic yet
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any prompt dispatch must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep the new handoff layer aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human acceptance requirements
