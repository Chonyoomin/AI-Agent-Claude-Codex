# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Fix the remaining Phase 9F / 9E adapter-routing mismatch so Codex-side capacity-resume dispatch respects the long-run loop's Codex invocation control instead of incorrectly keying off the Claude invocation flag.

## Context
Codex re-reviewed the current Phase 9F repo state and found one remaining runtime bug:

1. The standalone `reprobe_capacity_and_resume(...)` Codex-side branch now correctly invokes `make_codex_adapter().wait_for_review(...)` when `invoke_adapter=True`, but the Phase 9E long-run integration still forwards the WRONG control flag into that branch. In `run_long_run_continuation(...)`, the `halted_capacity_unavailable` pre-hop path calls `reprobe_capacity_and_resume(..., invoke_adapter=invoke_claude_adapter)`. That means a Codex-side resume from `awaiting_codex_review` ignores `invoke_codex_adapter` / `--no-invoke-codex` and instead dispatches or suppresses Codex review based on the Claude flag. The new tests explicitly lock in this mismatched behavior by asserting that `invoke_codex_adapter=False` with `invoke_claude_adapter=True` still invokes Codex. This is a contract and operator-control bug: the long-run loop advertises separate `--no-invoke-codex` and `--no-invoke-claude` escape hatches, but the Codex-side capacity-resume path currently routes through the Claude one.

## Required fixes
- update the Phase 9E long-run `halted_capacity_unavailable` integration so Codex-side capacity resume honors the Codex invocation control, not the Claude invocation control
- preserve the existing intended behavior:
  - Claude-side reprobe resume still uses the Claude invocation control for implementation/fix prompt dispatch
  - Codex-side reprobe resume still actively invokes the Codex adapter when the Codex invocation control allows it
  - explicit dry-run / no-invoke behavior still skips the relevant adapter dispatch cleanly
- preserve the existing hard-stop boundaries:
  - no Phase 9G final human acceptance automation
  - no automatic next-phase activation
  - no rewrite of the Phase 4 planner / activation separation
- keep canonical artifacts authoritative:
  - `loop-state.json`, retry-state, checkpoints, prompt/review artifacts, and logs remain the source of truth
  - retry-state remains an auditable support artifact, not a parallel control plane
- do not silently route a Codex-side resume through a Claude prompt handoff
- unsupported or ambiguous suspended statuses must still refuse fail-closed
- add focused tests proving:
  - a long-run Codex-side capacity resume does NOT invoke Codex when `invoke_codex_adapter=False` / `--no-invoke-codex`
  - a long-run Codex-side capacity resume DOES invoke Codex when `invoke_codex_adapter=True`
  - Claude-side resume behavior still respects the Claude invocation control
  - README/help text/tests no longer claim or lock in the current flag mismatch

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe runtime change that restores correct adapter ownership semantics across the Phase 9E -> Phase 9F seam

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
