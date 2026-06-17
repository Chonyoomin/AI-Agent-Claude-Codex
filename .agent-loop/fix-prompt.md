# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9E - Long-Run Continuation And Completion Heuristics)

## Objective
Fix the remaining Phase 9E runtime gap so the shipped long-run continuation layer actually extends the existing Phase 6 continuation primitives instead of stopping at a captured halt and requiring a separate manual resume or auto-continue step.

## Context
Codex re-reviewed the current Phase 9E repo state and found one remaining implementation bug:

1. `run_long_run_continuation(...)` only wraps Phase 9D hops. When a hop encounters a token-exhaustion-style Phase 6 continuation halt, Phase 9E records the halt in `.agent-loop/long-run-continuation.json` and stops, but it does not invoke or integrate the shipped Phase 6 continuation path. That conflicts with the active Phase 9E task and definition of done, which explicitly say this slice should extend the shipped Phase 6 continuation primitives and preserve checkpoint/resume behavior as part of the long-run continuation surface. The current behavior leaves the Phase 6 seam outside the Phase 9E runtime and still requires a separate operator action to continue the run.

## Required fixes
- integrate the shipped Phase 6 continuation primitives into the Phase 9E long-run continuation flow in a bounded, explicit way
- preserve the existing hard-stop model:
  - no automatic next-phase activation
  - no Phase 9F capacity re-probe logic
  - no Phase 9G final acceptance automation
- keep canonical artifacts authoritative:
  - `loop-state.json`, checkpoints, prompt artifacts, review artifacts, and evidence remain the source of truth
  - `.agent-loop/long-run-continuation.json` remains advisory
- do not silently widen autonomy:
  - only continue through already-shipped, bounded Phase 6 continuation behavior
  - refuse or stop cleanly on malformed state, exhausted continuation budgets, or unsupported halt states
- add focused tests proving:
  - a long-run hop that lands in the shipped token-exhaustion continuation halt can continue through the existing Phase 6 continuation path without requiring a separate manual command
  - bounded continuation still stops cleanly when continuation budget or hop budget is exhausted
  - malformed or unsupported continuation state is still refused fail-closed
  - the existing approved / failed / halted completion detection behavior remains intact

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9E scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not rewrite the Phase 4 planner / activation boundary
- do not replace canonical checkpoint / loop-state behavior with transcript-only or runtime-only state
- prefer the smallest safe runtime change that closes the contract gap

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
