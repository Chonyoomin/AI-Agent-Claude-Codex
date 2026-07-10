# Claude Code Task

## Phase
Fix Phase B2 - Desktop Bootstrap Form And Validation

## Objective
Implement the bounded desktop bootstrap form and validation layer for
empty-target project setup, so the operator can enter the required bootstrap
fields safely inside the desktop app before any later dispatch slice.

## Context
Fix Phase B1 is complete. The repo now has the approved desktop bootstrap UX
contract:

- target folders are classified as `empty_target`, `full_target`,
  `partial_target`, or `malformed_target`
- `empty_target` enters the bootstrap path
- `full_target` surfaces attach guidance
- `partial_target` and `malformed_target` refuse fail-closed
- the desktop shell is currently guidance-only and does NOT dispatch canonical
  attach/bootstrap mutation from Tk callbacks

This slice is the next bounded step. Add the in-app form-and-validation layer
for bootstrap input capture, but do not widen into direct bootstrap dispatch.
The shipped runtime and canonical artifacts remain the source of truth.

## Required work
- implement or refine the bounded desktop bootstrap form flow for
  `empty_target` project setup so the operator can enter:
  - `attached_by`
  - `approval_mode`
  - `bootstrapped_by`
  - `human_objective`
  - `project_intent`
- ensure the form validates those fields fail-closed in the desktop flow:
  - missing values refused
  - empty or whitespace-only values refused
  - any other unsupported input shape explicitly refused where required by the
    current desktop guidance contract
- preserve typed operator context on validation failure so the user can correct
  fields instead of re-entering everything from scratch
- preserve the existing explicit refusal behavior for:
  - `partial_target`
  - `malformed_target`
- keep the bootstrap form/operator flow clearly separate from:
  - attach-existing-project flow
  - first-phase activation
  - actual bootstrap dispatch
- add or update focused tests for the form/validation behavior

## Constraints
- Follow `CLAUDE.md`.
- Stay narrowly focused on the desktop bootstrap form and validation layer.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not silently transition canonical phase/task artifacts.
- Do not reintroduce direct desktop-side dispatch to
  `attach_external_target(...)`.
- Do not invent hidden defaults for `attached_by`, `bootstrapped_by`,
  `human_objective`, or `project_intent`.
- Do not weaken the shipped `partial_target` / `malformed_target` refusal
  behavior.
- Prefer small, testable, reversible changes.

## Important guardrails
- Reuse the shipped Phase 10C / 10E bootstrap runtime vocabulary rather than
  inventing a second desktop-only state plane.
- Do not silently bootstrap merely because a folder was selected.
- Do not claim the desktop app can fully bootstrap and start a project unless
  the actual code in this slice truly does that.
- Keep this slice centered on input capture, validation, and bounded desktop
  UX behavior.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- any other focused desktop/bootstrap tests you need to update

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
