# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9G - Final Human Acceptance And Polish Gate)

## Objective
Remove the remaining stale Phase 9G non-mutation wording so the shipped code/tests describe the current canonical accepted-state behavior accurately.

## Context
Codex re-reviewed the updated Phase 9G repo state and found one residual mismatch:

1. The implementation now correctly transitions `loop-state.status` to `phase_complete_final_human_accepted` during `record_final_acceptance(...)`, and the README plus most tests were updated to match. However, the `record_final_acceptance(...)` docstring in `scripts/agent_loop.py` still says "The function does NOT mutate loop-state.json", and the top-of-file test contract comment in `tests/test_final_acceptance.py` still says "the recorder does NOT mutate loop-state". Those statements are now false. This is no longer a runtime bug, but it is still a shipped contract/documentation mismatch inside the authoritative code/test surface.

## Required fixes
- update the stale Phase 9G wording in the remaining code/test self-documentation so it matches the current implementation:
  - `scripts/agent_loop.py`
  - `tests/test_final_acceptance.py`
- preserve the actual shipped behavior:
  - `record_final_acceptance(...)` writes the artifact first, then transitions only `loop-state.status`
  - no other loop-state fields are mutated
  - recording remains a gate, not an activation
  - explicit human acceptance, artifact validation, and re-record refusal behavior remain unchanged
- keep scope narrow: this is an internal consistency/docstring cleanup, not new Phase 9 behavior
- update `.agent-loop/claude-summary.md` with the focused fix and validation evidence

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9G scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe text-only/code-comment/docstring change that removes the stale non-mutation wording

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include focused validation showing the remaining stale wording is gone.
