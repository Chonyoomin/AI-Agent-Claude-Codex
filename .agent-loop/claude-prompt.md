# Claude Code Task

## Phase
Fix Phase B1 - Desktop Bootstrap UX Contract

## Objective
Define and implement the bounded desktop UX contract for bootstrapping a new
empty target project from the desktop app, so selecting a brand-new folder no
longer stops at the raw `empty_target` refusal wall.

## Context
The shipped runtime already supports explicit empty-target bootstrap through the
existing external-target path:

- `attach-external-target --bootstrap`
- `--bootstrapped-by`
- `--human-objective`
- `--project-intent`

The gap is desktop UX. Today the operator can point the app at a folder, but
when that folder is an `empty_target`, the desktop flow only surfaces the
Phase 10C/10E refusal instead of giving the operator a bounded bootstrap path.

This task is the first slice only. Stay at the UX-contract layer: define how
the desktop app should detect `empty_target`, when it should present bootstrap
vs attach-existing-project choices, which fields are required, and how the UI
must explain the next step. Do not widen into a broad architecture rewrite.

Work against the actual desktop implementation in `scripts/agent_loop.py` and
the current desktop project-start / attach surfaces. Reuse the shipped
external-target bootstrap runtime boundaries rather than inventing a second
desktop-only bootstrap state plane.

## Required work
- define the desktop-side UX contract for handling target-folder selection when
  the selected folder is:
  - `empty_target`
  - `full_target`
  - `partial_target`
  - `malformed_target`
- implement the first bounded desktop UX behavior for the `empty_target` case
  so the operator is routed toward bootstrap rather than only seeing a raw
  refusal
- make the contract explicit about when the UI is in:
  - attach-existing-project mode
  - bootstrap-new-project mode
- make the required bootstrap fields explicit in the desktop flow:
  - `attached_by`
  - `approval_mode`
  - `bootstrapped_by`
  - `human_objective`
  - `project_intent`
- preserve the explicit-operator-input rule; do not auto-fill identity,
  objective, or intent fields from OS state, environment variables, or hidden
  defaults
- ensure the desktop app explains that bootstrap is distinct from first phase
  activation and that a bootstrapped target still lands in
  `awaiting_first_activation`
- add or update focused tests for the desktop bootstrap UX contract behavior

## Constraints
- Follow `CLAUDE.md`.
- Stay narrowly focused on the desktop bootstrap UX contract and directly
  related desktop view or renderer changes.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not silently transition the canonical phase/task artifacts to Fix Phase B;
  that task-state work remains Codex-owned unless explicitly reassigned.
- Do not introduce a second bootstrap runtime, hidden state store, or
  background control plane.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

## Important guardrails
- Reuse the shipped Phase 10C/10E bootstrap runtime contract instead of
  bypassing it for UI convenience.
- Do not silently bootstrap merely because a folder was selected.
- Do not weaken refusal behavior for `partial_target` or `malformed_target`.
- Do not claim the UI can fully bootstrap and start a project unless the actual
  bounded implementation in this slice really does so.
- Keep this slice centered on UX contract and operator guidance, not on broad
  runtime expansion.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_desktop_project_start.py`
- `tests/test_desktop_action_bridge.py`
- any other focused desktop/external-target/bootstrap tests you need to update

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
