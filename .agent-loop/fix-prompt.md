# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9G - Final Human Acceptance And Polish Gate)

## Objective
Close the remaining Phase 9G contract gap so explicit final human acceptance is reflected in the canonical state model, not only in the separate `.agent-loop/final-acceptance.json` evaluator path.

## Context
Codex re-reviewed the current Phase 9G repo state and found one remaining issue:

1. The shipped Phase 9G slice records final human acceptance into `.agent-loop/final-acceptance.json` and `evaluate_final_acceptance(...)` can report `final_acceptance_recorded`, but the canonical loop-state model still stops at `status == "phase_complete_awaiting_human_approval"` with `last_verdict == "APPROVED_FOR_HUMAN_REVIEW"`. The Phase 9G task contract explicitly says Codex should update the canonical phase/task artifacts to reflect the accepted terminal state rather than relying on runtime-only signals. Today `record_final_acceptance(...)` intentionally does not mutate `loop-state.json`, `cmd_record_final_acceptance(...)` repeats that contract, the tests assert the non-mutation behavior, and the README documents the same split-state model. That leaves final human acceptance authoritative only through the separate artifact/evaluator path instead of being representable in the canonical state model itself.

## Required fixes
- implement the narrowest safe Phase 9G change that makes accepted completion visible through the canonical state model, not only through `.agent-loop/final-acceptance.json`
- keep the explicit human gate intact:
  - no silent auto-acceptance
  - no bypass of the required `accepted_by` / optional `notes` recording flow
  - no automatic next-phase activation behavior
- update the relevant runtime/docs/tests together so the contract is internally consistent:
  - `scripts/agent_loop.py`
  - `tests/test_final_acceptance.py`
  - `README.md`
  - `.agent-loop/claude-summary.md`
- preserve the existing fail-closed behavior for malformed loop-state, malformed acceptance artifacts, stale acceptance artifacts, output-boundary violations, and re-acceptance without explicit delete/re-record
- keep scope limited to the Phase 9G final-acceptance contract gap; do not widen into new Phase 9 features

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9G scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest coherent implementation that removes the split-brain between accepted completion and canonical loop-state

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include focused validation showing the new canonical accepted-state behavior.
