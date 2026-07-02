# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10Y review issues found by Codex.

## Context
The latest Phase 10Y implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/phase-plan.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_resume_console.py`
- `README.md`
- `TASK.md`

## Required fixes
- Fix the Phase 10Y resume-button enablement bug in `scripts/agent_loop.py`.
  `build_desktop_resume_console_controls(...)` currently enables `resume`
  whenever `capacity_halt_state != "not_halted"`. That incorrectly enables the
  button for the `unknown` state produced when the resume-console view cannot
  read a valid loop-state snapshot. Per the 10Y contract, `resume` should be
  enabled only when an actual confirmed halt is in flight; the `unknown` path
  must fail closed.
- Add focused regression coverage in `tests/test_desktop_resume_console.py` for
  the unreadable or unknown-state path. The tests should fail if `resume`
  remains enabled when the derived `capacity_halt_state` is `unknown`, while
  preserving the existing expected behavior for token-exhaustion and other real
  halted states.
- Update `README.md` only if needed so the 10Y description stays exactly
  aligned with the shipped behavior after the code fix.
- Keep the fix inside the approved Phase 10Y boundaries. Do not add token
  refresh, hidden auto-resume, retry/backoff machinery, concurrency, packaging,
  or any mutating control plane.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10Z+.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not widen the Phase 10I three-control library-callable cap.
- Preserve the resume console as a read-only, canonical-artifact-derived
  surface.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
