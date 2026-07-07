# Claude Code Task

## Phase
Desktop App UI Simplification Task

## Objective
Simplify the desktop app UI so the operator only sees three primary controls:

- a `Run` button that changes to `Stop` while the program is running
- a `Code Review` button for triggering the Codex review path
- an approval-mode selector dropdown for choosing which approval mode to run in

## Context
The current desktop app in `scripts/agent_loop.py` has accumulated many
control panels and copy-paste affordances. The goal of this task is to make
the operator-facing UI substantially simpler and more direct for normal use.

Work against the actual shipped desktop-app window implementation in
`_launch_desktop_app_window(...)` and its related view/control builders. The
intended outcome is a much smaller control surface that prioritizes:

1. starting/stopping the agent loop
2. triggering code review
3. selecting approval mode

Do not redesign the entire product. Keep this task focused on reducing the
visible operator controls and making the main workflow obvious.

## Required work
- update the native desktop app UI so the primary visible controls are reduced
  to:
  - `Run` / `Stop` toggle button
  - `Code Review` button
  - approval-mode dropdown selector
- ensure the `Run` button visibly changes to `Stop` while a run is in progress
  and flips back when the run is no longer active
- wire the approval-mode dropdown to the existing shipped approval-mode
  vocabulary (`review`, `strict`, `autonomous`) rather than inventing new mode
  names
- make the simplified control area usable at normal window sizes without the
  current overwhelming stack of control buttons
- preserve the existing desktop status/readout area unless a small adjustment is
  needed to support the simplified controls cleanly
- remove, hide, or collapse the large existing button stacks/panels that are no
  longer meant to be primary operator controls
- add or update focused tests covering the new simplified UI behavior

## Constraints
- Follow `CLAUDE.md`.
- Stay focused on the desktop-app UI and the directly related control wiring.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated phases, contracts, or desktop sub-views that are not
  necessary for this UI simplification.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

## Important guardrails
- Reuse existing shipped approval-mode concepts and runtime/control wiring where
  possible; do not invent a hidden second state plane for approval mode.
- Do not silently widen the desktop app into a hidden autonomous orchestrator
  beyond what the shipped runtime already supports.
- Keep the UI simpler, not broader.
- If a current control surface is only useful for secondary or advanced flows,
  it should no longer dominate the main window.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- any other focused desktop-app test file you need to adjust

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
