# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Fix the remaining Phase 9F runtime gap so a successful capacity re-probe resumes the exact suspended work step, not just the persisted `loop-state.status` string.

## Context
Codex re-reviewed the current Phase 9F repo state and found one remaining implementation bug:

1. `reprobe_capacity_and_resume(...)` restores `loop-state.status` and deletes the retry-state, but it does not actually resume the suspended step. The success path ends immediately after `save_loop_state(..., {"status": retry_state["suspended_status"]})` and returns. The CLI wrapper also exits after printing "status restored". In the Phase 9E integration path, the next hop sees a non-terminal restored status and falls straight into `run_internal_review_fix_cycle(...)`, which is not the same thing as resuming the original suspended step. For example, if the capacity halt was recorded while `status == "claude_implementing"`, a successful re-probe restores that status but does not dispatch Claude implementation; the long-run loop then advances into the Phase 9D review/fix path instead. That falls short of the active 9F task and definition of done, which require resuming the exact suspended step automatically when capacity returns.

## Required fixes
- make the successful Phase 9F resume path continue the actual suspended work step, not just restore the status field
- preserve the existing narrow scope:
  - no Phase 9G final human acceptance automation
  - no automatic next-phase activation
  - no rewrite of the Phase 4 planner / activation separation
- keep canonical artifacts authoritative:
  - `loop-state.json`, retry-state, checkpoints, prompt/review artifacts, and logs remain the source of truth
  - retry-state remains an auditable support artifact, not a parallel control plane
- ensure the resume target is consistent with the stored suspended state
  - a resumed `claude_implementing` halt should continue the Claude implementation path
  - a resumed `claude_fixing` halt should continue the Claude fix path if that status is supported
  - unsupported or ambiguous suspended states should still refuse fail-closed rather than silently routing to the wrong step
- update the Phase 9E integration so a successful capacity reprobe resumes through the correct suspended-step continuation rather than dropping into the generic Phase 9D review/fix path
- add focused tests proving:
  - a capacity halt recorded from a real in-flight status resumes the matching suspended step automatically after a successful re-probe
  - the long-run integration does not misroute a resumed `claude_implementing` halt into Phase 9D review/fix
  - unsupported suspended states still refuse fail-closed

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe runtime change that closes the suspended-step routing gap

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
