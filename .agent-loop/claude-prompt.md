# Claude Code Task

## Phase
Phase 9G - Final Human Acceptance And Polish Gate

## Objective
Implement the Final Human Acceptance And Polish Gate slice for the agent loop. This slice should require an explicit final human review, polish, and acceptance step before a fully autonomous PRD-to-product run is treated as complete, using canonical repo artifacts and preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Context
Implement the Final Human Acceptance And Polish Gate slice for the agent loop. This slice should require an explicit final human review, polish, and acceptance step before a fully autonomous PRD-to-product run is treated as complete, using canonical repo artifacts and preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9G as active
- `.agent-loop/phase-plan.md` records Phase 9F as closed history and contains a `## Phase 9G - Final Human Acceptance And Polish Gate` section with concrete objective, done criteria, and exclusions
- the repository ships a bounded final human acceptance / polish gate for the fully autonomous Phase 9 runtime that extends the shipped Phase 9B/9C/9D/9E/9F surfaces
- the runtime detects the final acceptance boundary from canonical artifacts and refuses to treat the run as complete until explicit human acceptance is recorded
- the new surface preserves the shipped artifact/source-of-truth boundary:
  - canonical prompt, summary, review, fix, checkpoint, retry-state, loop-state, and final-acceptance artifacts remain authoritative
  - advisory descriptors remain routing/timing artifacts only
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves final-acceptance gating behavior, refusal behavior, and hard-stop preservation from repo artifacts and logs
- `README.md` reflects that Phase 9G is active and that the final human acceptance / polish gate is now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no auto-accepting product completion or silently skipping the explicit final human gate
- no automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous, reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation, runtime-adapter, or LangChain support-layer behavior beyond the narrow final human acceptance / polish gate seam
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no MCP support, external UI, or concurrent-agent operation in this slice
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
