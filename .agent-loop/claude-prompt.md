# Claude Code Task

## Phase
Fix Phase C2 - Project Folder Picker And Classification Surface

## Objective
Implement the first guided desktop setup step: let a non-technical operator
choose a project folder and show a plain-English classification and next action
for the selected folder.

## Context
Fix Phase C1 is complete and approved for human review. Its contract is at
`docs/desktop-first-run-setup-contract.md`; read it before editing. C2 is the
first runtime slice under that contract. Work against the actual repo state and
do not rely on prior chat context.

## Required work
- add an OS-native folder-picker action to the shipped desktop app surface so
  the operator does not need to type a terminal path
- route the selected folder through the shipped target inspection / attach
  helpers; do not duplicate target classification logic in the UI
- surface the closed classifications in plain English:
  `existing_project`, `empty_folder`, `partial_target`, and
  `malformed_target`
- provide a clear next action for every classification:
  attach the existing project, offer the later bootstrap path for an empty
  folder, or explain how to recover from a partial or malformed target
- preserve the C1 default surface: `Project` remains the first setup section,
  technical runtime vocabulary remains behind the existing Advanced surface,
  and no raw CLI refusal becomes the primary user-facing message
- preserve canonical-artifact-first behavior and the shipped desktop polling
  cadence; do not create a UI-only target-state cache or second controller
- add focused tests for picker wiring, classification mapping, plain-English
  next-step messaging, and fail-closed partial/malformed handling
- update `README.md` and `.agent-loop/claude-summary.md` with the shipped
  behavior and validation performed

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md` or `CLAUDE.md`.
- Do not add PRD selection, run-mode selection, Start/Stop controls, or the
  run console; those belong to Fix Phase C3-C8.
- Do not invent a hidden UI-only JSON, SQLite, MessagePack, or in-memory
  persistence plane that survives a refresh/session.
- Do not silently bootstrap a new project from folder selection alone; expose
  the classification and defer bootstrap dispatch to the shipped bootstrap
  surface / later bounded slice.
- Do not weaken refusal behavior for partial or malformed targets.
- Do not add Git automation, background watchers, or network endpoints.

## Important guardrails
- The desktop app is a control/reporting surface over shipped runtime helpers,
  not a second source of truth.
- Explicit operator gestures are required; selecting a folder must not
  auto-advance into PRD intake or agent execution.
- Keep technical details available only through the existing Advanced toggle.
- Prefer small, testable, reversible changes.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_external_workspace.py`
- `README.md`
- `docs/desktop-first-run-setup-contract.md`

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the
required Claude Implementation Summary format and include the validation you
ran.
