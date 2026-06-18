# Claude Code Task

## Phase
Phase 9E - Long-Run Continuation And Completion Heuristics

## Objective
Implement the Long-Run Continuation And Completion Heuristics slice for the agent loop. This slice should extend the shipped Phase 6 continuation primitives and the Phase 9B/9C/9D autonomous runtime so the orchestrator can continue across longer product-building runs, detect bounded “done enough” completion states from canonical artifacts, and stop or continue deterministically without silently widening autonomy, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Context
Implement the Long-Run Continuation And Completion Heuristics slice for the
agent loop. This slice should extend the shipped Phase 6 continuation
primitives and the Phase 9B/9C/9D autonomous runtime so the orchestrator can
continue across longer product-building runs, detect bounded “done enough”
completion states from canonical artifacts, and stop or continue
deterministically without silently widening autonomy, while preserving the
shipped planner/activation boundary, artifact source-of-truth model, and
hard-stop behavior.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9E as active
- `.agent-loop/phase-plan.md` records Phase 9D as closed history and contains a
  `## Phase 9E - Long-Run Continuation And Completion Heuristics` section with
  concrete objective, done criteria, and exclusions
- the repository ships a bounded long-run continuation layer that can extend
  the autonomous Phase 9 runtime across multiple continuation hops using
  canonical repo artifacts and the shipped Phase 6 continuation primitives
- the runtime can detect bounded completion / “done enough” terminal states
  from canonical artifacts and explicit review signals rather than relying on
  transcript-only judgment
- the new surface preserves the shipped artifact/source-of-truth boundary:
  canonical prompt, summary, review, fix, checkpoint, and loop-state artifacts
  remain authoritative; advisory descriptors remain routing/timing artifacts
  only
- the new surface preserves the shipped CLI-first workflow,
  planner/activation boundaries, approval semantics, halt/refusal vocabulary,
  checkpoint/resume behavior, cycle thresholds, and repo-artifact
  source-of-truth model
- focused validation proves bounded long-run continuation behavior,
  completion-detection behavior, refusal behavior, and hard-stop preservation
  from repo artifacts and logs
- `README.md` reflects that Phase 9E is active and that long-run continuation /
  completion heuristics are now the implementation focus

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
- no capacity-halt re-probe or final acceptance automation (Phases 9F-9G)
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no MCP support, external UI, or concurrent-agent operation in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
