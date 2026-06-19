# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Fix the remaining Phase 9F contract gap so the capacity-halt seam supports both Claude-side and Codex-side capacity exhaustion, not only Claude-side suspended statuses.

## Context
Codex re-reviewed the current Phase 9F repo state and found one remaining implementation bug:

1. The new Phase 9F resume routing is explicitly restricted to `claude_implementing` and `claude_fixing`. `CAPACITY_RETRY_SUPPORTED_SUSPENDED_STATUSES` excludes non-Claude statuses, and the tests now explicitly assert that `awaiting_codex_review` and `evidence_capture` are refused fail-closed. That means the shipped Phase 9F surface does not currently support Codex-side capacity exhaustion, even though the active Phase 9F task and definition of done say this slice should treat **Claude/Codex** token or rate-limit exhaustion as a resumable external-capacity halt.

## Required fixes
- extend the Phase 9F capacity-halt seam so Codex-side capacity exhaustion is supported too, not just Claude-side suspended statuses
- preserve the existing hard-stop boundaries:
  - no Phase 9G final human acceptance automation
  - no automatic next-phase activation
  - no rewrite of the Phase 4 planner / activation separation
- keep canonical artifacts authoritative:
  - `loop-state.json`, retry-state, checkpoints, prompt/review artifacts, and logs remain the source of truth
  - retry-state remains an auditable support artifact, not a parallel control plane
- add supported routing for any newly-allowed Codex-side suspended statuses so a successful reprobe resumes the correct step instead of silently misrouting
- unsupported or ambiguous suspended statuses must still refuse fail-closed
- add focused tests proving:
  - a capacity halt recorded from a Codex-side suspended status can be resumed successfully through the correct continuation path
  - the long-run / autonomous path handles that Codex-side capacity halt without misrouting
  - malformed or unsupported suspended statuses still refuse fail-closed

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe runtime change that closes the Claude/Codex parity gap

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
