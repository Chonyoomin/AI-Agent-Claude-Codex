# Current Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode

## Sub-Phase
Phase 9D - Autonomous Internal Review/Fix Loop

## Status
Phase 9D is active as the next runtime-building slice under the approved Phase 9 autonomy contract. The goal is to let the orchestrator autonomously run the internal Codex review plus Claude fix loop across bounded cycles while preserving the existing ownership boundary, artifact truth, review semantics, and halt/audit behavior.

## Task
Implement the Autonomous Internal Review/Fix Loop slice for the agent loop. This slice should let the orchestrator consume the Phase 9B/9C handoff artifacts, trigger Codex review automatically, route findings by owner, regenerate `.agent-loop/fix-prompt.md` when Claude-owned fixes are required, and continue bounded internal review/fix cycles without manual routing between agents, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Notes

- keep this slice narrow: implement autonomous internal review/fix continuation only; do not broaden into automatic next-phase activation, long-run completion heuristics, capacity re-probe, or final-run completion logic yet
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any review/fix continuation must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep the new handoff layer aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human acceptance requirements
