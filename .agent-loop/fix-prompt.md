# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10X review issues found by Codex.

## Context
The latest Phase 10X implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/phase-plan.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_run_console.py`
- `tests/test_documentation_consistency.py`
- `README.md`
- `TASK.md`

## Required fixes
- Fix the Phase 10X completion-ledger ordering bug. In current repo state, the
  run console marks completed phases `10P` through `10W` as `pending` because
  the newly-added `## Phase 10X - Autonomous Run Console And Completion Ledger`
  section was inserted before those already-completed phase sections in
  `.agent-loop/phase-plan.md`, and the stale `10W` section still says `Active`.
  Restore canonical chronological phase-plan history so the shipped
  `view-desktop-run-console` output reports already-completed phases as
  `complete` and only the active phase as `in_progress`.
- Add focused regression coverage for that ledger-ordering/canonical-history
  behavior. The tests should fail if a completed phase after the inserted 10X
  block can still surface as `pending`, or if stale phase-plan active markers
  contradict the current active phase without being caught.
- Fix the Phase 10X activity-label mismatch in `scripts/agent_loop.py`.
  `_run_console_derive_activity_state(...)` currently maps
  `awaiting_claude_implementation` to `awaiting_fix` unconditionally, which
  makes the run console label the normal pre-implementation state as a fix
  state even when `fix_cycle_state='not_in_fix_cycle'`. Make the activity label
  and the fix-cycle label semantically consistent for the non-fix
  `awaiting_claude_implementation` path.
- Update `README.md` so the Phase 10X description matches the shipped behavior
  after the code fix. The docs should not describe the normal
  `awaiting_claude_implementation` path as “awaiting Claude fix” unless the
  runtime actually gates that label on an active fix cycle.
- Keep the fix inside the approved Phase 10X boundaries. Do not add auto-resume,
  retry/backoff runtime, model/policy selection, concurrency, packaging,
  hidden orchestration, or any new mutating control plane.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10Y+.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not widen the Phase 10I three-control library-callable cap.
- Preserve the run-console as a read-only, canonical-artifact-derived surface.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
