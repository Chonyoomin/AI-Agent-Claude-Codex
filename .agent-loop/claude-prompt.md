# Claude Code Task

## Phase
Desktop App UI Improvement Task

## Objective
Add a native folder-browse flow to the desktop app so an operator can point the
agent at a target project folder from the UI instead of manually typing or
copy-pasting a path-oriented CLI command.

## Context
The project already has external-target and project-start support in the
runtime (`attach-external-target`, external-target inspection, project-start
views), but the desktop UX still needs a more natural folder-selection flow.

The goal of this task is to add a proper project-folder selection UX to the
desktop app and wire it into the existing shipped external-target attach flow.
This should feel like a normal desktop app action: click a button, browse for a
folder, and attach/select that project for the agent.

Work against the actual desktop window implementation in
`scripts/agent_loop.py`, especially the Tk window and the existing
external-target / project-start surfaces.

## Required work
- add a native folder-browse UI flow to the desktop app for selecting a target
  project folder
- use a normal desktop folder-picker/dialog rather than requiring the operator
  to type a raw path into the UI
- wire the selected folder into the shipped external-target attach/project-start
  flow rather than inventing a parallel hidden target-selection state plane
- make the selected project visible in the UI after selection so the operator
  can tell what folder the agent is pointed at
- preserve the existing controller-root versus external-target distinction; do
  not silently collapse them into one concept
- preserve the existing safety boundaries around target attachment and
  validation
- update the desktop UI so this project-folder selection flow is a primary,
  operator-friendly path
- add or update focused tests for the new browse-and-attach behavior

## Constraints
- Follow `CLAUDE.md`.
- Stay focused on the desktop app, external-target attach flow, and directly
  related UI/runtime wiring.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated runtime phases or contracts unless needed to support
  the bounded UI flow.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

## Important guardrails
- Reuse the shipped external-target runtime instead of creating a second hidden
  “selected project” state store.
- Do not bypass the existing attach validation and refusal behavior.
- Do not silently mutate unrelated loop-state fields just because a project
  folder was selected.
- Keep this as a desktop UX improvement, not a broad architecture rewrite.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_desktop_project_start.py`
- `tests/test_desktop_action_bridge.py`
- any other focused desktop/external-target tests you need to update

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
