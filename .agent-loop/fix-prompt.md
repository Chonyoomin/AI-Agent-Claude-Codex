# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Close the remaining Phase 9F automatic-resume gap for Codex-side capacity halts so a successful capacity reprobe resumes the exact suspended Codex review step, not just the loop-state status.

## Context
Codex re-reviewed the current Phase 9F repo state. The Claude/Codex parity allowlist fix is already present, but one runtime gap remains:

1. The Codex-side resume branch for `awaiting_codex_review` restores `loop-state.status` and records `handoff_mode='codex_review_pending'`, but it does not actually resume the suspended Codex review step in the reprobe success path. `reprobe_capacity_and_resume(...)` explicitly returns after restoring the status, and `cmd_reprobe_capacity_and_resume(...)` also just prints success and exits. The current tests lock in this restore-only behavior. That falls short of the active Phase 9F contract in `.agent-loop/phase-plan.md`, which says the system should "resume the exact suspended step automatically when capacity returns." In the long-run path, the next hop can eventually consume the restored status, but the standalone success path and the current tests still do not prove or deliver automatic Codex-side step resumption.

## Required fixes
- update the Codex-side `awaiting_codex_review` success path so a successful capacity reprobe resumes the suspended Codex review step automatically instead of only restoring status
- preserve the existing Claude-side behavior:
  - `claude_implementing` still resumes through implementation prompt handoff
  - `claude_fixing` still resumes through fix prompt handoff
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
  - a successful reprobe from `awaiting_codex_review` resumes the Codex review continuation automatically in the intended runtime path
  - the standalone CLI success path no longer stops at restore-only behavior
  - the long-run / autonomous path still handles the Codex-side capacity halt correctly without Claude misrouting
  - malformed or unsupported suspended statuses still refuse fail-closed

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe runtime change that closes the Codex-side automatic-resume gap without widening the Phase 9C handoff contract unnecessarily

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
