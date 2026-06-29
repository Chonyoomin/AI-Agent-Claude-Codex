# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10Q review issues found by Codex.

## Context
The latest Phase 10Q implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_run_profiles.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/desktop-app-contract.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the three `select_approval_mode_*` run-profile affordances so they are
  genuinely actionable and do not mislead the operator. The current affordance
  "command" is only `python scripts/agent_loop.py plan` followed by an inline
  shell comment explaining what the human should edit before running
  `activate`, which means a copy-paste of the displayed command does NOT
  actually encode or apply the selected approval mode. Update the Phase 10Q
  desktop run-profiles surface so the approval-mode affordance path is explicit
  and operator-actionable instead of a misleading partial command.
- Fix the Phase 10Q desktop-app surface so it actually provides a first-class
  desktop control surface rather than only advisory text inside the Tkinter
  `ScrolledText` window. The current implementation renders `Run Profiles
  (Phase 10Q)` as text, but does not provide actual desktop-side controls,
  buttons, or toggles for selecting a run profile from the app itself. Update
  the shipped desktop app so the 10Q surface satisfies the phase goal of
  explicit desktop controls while preserving the existing Phase 10L/10M/10N
  safety boundaries.
- Add or update focused tests for both fixes:
  - coverage proving approval-mode selection is surfaced through an actionable,
    non-misleading operator path
  - coverage proving the desktop app exposes real Phase 10Q control widgets or
    equivalent explicit desktop-side controls, not just advisory rendered text
- Update `README.md` as needed so the 10Q description matches the shipped
  implementation after the fixes.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10R, 10S, 10T, or 10U.
- Do not introduce a hidden persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state outside
  approved canonical write paths.
- Do not add subprocess spawning, shell execution, network IO, or canonical
  artifact writes beyond the shipped bounded desktop/runtime contracts.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10Q objective and existing Phase 10L/10M/10N
  non-mutation boundaries.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
