# Claude Code Fix Task

## Objective
Fix the remaining Phase 8B README inconsistency so every strict-mode gate-count
reference in the README matches the shipped Phase 5C contract exactly.

## Context
Codex re-reviewed the current Phase 8B fix pass from repo state. The prior
README drift in the Phase 5D and Phase 8B paragraphs is fixed, the new focused
README tests pass, and the full test suite passes. One Claude-owned README
defect still remains:

1. `README.md` still says, in the `tests/test_approval_modes.py` bullet, that
   "Autonomous-mode coverage proves none of the four strict gates fires under
   `autonomous`." That wording is still inaccurate relative to the shipped
   runtime contract:
   - the shipped Phase 5C contract defines three strict-mode gates:
     `pre_claude_prompt`, `pre_fix_prompt`, and `pre_codex_review`
   - `pre_codex_review` persists in two halt-status flavors
     (`halted_awaiting_human_pre_codex_review_normal` and
     `halted_awaiting_human_pre_codex_review_fix`) so resume can route
     correctly
   - the README therefore still contains an internal contradiction even after
     the last fix cycle

The remaining `.agent-loop/phase-plan.md` wording drift is Codex-owned and is
NOT part of this Claude fix task.

## Required fixes
- Correct the `tests/test_approval_modes.py` bullet in `README.md` so it no
  longer says "four strict gates" and instead describes the shipped behavior in
  a way that is consistent with the corrected Phase 5D and Phase 8B paragraphs.
- Extend the focused documentation-consistency coverage so this remaining README
  variant also fails closed on regression. The current README guard only blocks
  two specific phrases and does not catch the still-present "four strict gates"
  wording in the test-description bullet.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final
  fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 8B scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit Codex-owned planning artifacts such as `.agent-loop/phase-plan.md`,
  `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or
  `.agent-loop/codex-review.md`.
- Do not broaden into new runtime, approval-mode, halt, or checkpoint behavior.
- Preserve the shipped contracts and describe only behavior that already exists
  in the repo.
- Prefer the smallest safe documentation/test fix that makes the README
  internally consistent relative to the current runtime.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the
required summary format and include the exact validation commands you ran.
