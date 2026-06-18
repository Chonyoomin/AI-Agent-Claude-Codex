# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9E - Long-Run Continuation And Completion Heuristics)

## Objective
Fix the remaining Phase 9E completion-accounting bug in the new token-exhaustion integration path so a successful Phase 6F resume that lands in a terminal completion state is recognized immediately, even when it happens on the final available hop.

## Context
Codex re-reviewed the current Phase 9E repo state and found one remaining runtime bug:

1. In `run_long_run_continuation(...)`, the new pre-hop `HALTED_TOKEN_EXHAUSTION` branch calls `run_token_exhaustion_resume(repo_root)`, stores `post_resume = evaluate_phase_completion(repo_root)`, and then always `continue`s on `rc == 0` instead of checking whether the restored state is already terminal. That means a successful resume that restores `phase_complete_awaiting_human_approval` + `APPROVED_FOR_HUMAN_REVIEW` (or another explicit terminal outcome) is only recognized on the next hop. If the successful resume happens on the last allowed hop, the loop exits through the generic "max hops exhausted" path and drops the terminal completion signal entirely. The current tests only cover the multi-hop case (`max_hops=3`) where a later hop catches the terminal state, so this edge case is currently untested.

## Required fixes
- update the pre-hop token-exhaustion resume branch so Phase 9E evaluates the post-resume state immediately
- if `run_token_exhaustion_resume(...)` returns `0` and the restored state is already terminal, set the final completion from that same hop and stop cleanly instead of requiring another hop
- preserve the existing bounded behavior:
  - no automatic next-phase activation
  - no Phase 9F capacity re-probe
  - no Phase 9G final acceptance automation
  - no widening beyond the shipped Phase 6F primitive
- keep canonical artifacts authoritative:
  - `loop-state.json`, checkpoints, review artifacts, and evidence remain the source of truth
  - `.agent-loop/long-run-continuation.json` remains advisory
- add focused tests proving:
  - a successful token-exhaustion resume on the final allowed hop still produces `completion_approved` immediately when the restored loop-state is already approved
  - the same immediate-terminal handling works for the failed/halted terminal path if applicable
  - non-terminal successful resumes still continue to a later hop exactly as before

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9E scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- do not rewrite the Phase 4 planner / activation boundary
- prefer the smallest safe runtime change that fixes the hop-accounting bug without disturbing the new Phase 6F seam

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
