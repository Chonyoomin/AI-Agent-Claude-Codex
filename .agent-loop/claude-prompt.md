# Claude Code Task

## Phase
Fix Phase B3 - Desktop Bootstrap Dispatch And Post-Bootstrap Handoff

## Objective
Wire the validated desktop bootstrap form into the shipped
`attach-external-target --bootstrap` runtime path, refresh the attached-target
view after success, and surface the first explicit post-bootstrap next-step
guidance without introducing a second bootstrap runtime or hidden desktop-only
state plane.

## Context
Fix Phase B1 established the desktop bootstrap UX contract and Fix Phase B2
added the bounded desktop form/validation layer. The remaining remediation gap
is runtime dispatch and post-bootstrap handoff.

Today the desktop bootstrap dialog validates input and surfaces a copy-paste
CLI, but the operator still has to leave the app and run the shipped bootstrap
command manually. This slice should close that gap by calling the existing
bootstrap runtime directly from the desktop path, while preserving the shipped
controller-vs-target boundaries, artifact truth, and refusal behavior.

Work against the actual desktop implementation in `scripts/agent_loop.py` and
reuse the shipped `attach_external_target(..., bootstrap=True, ...)` path
rather than inventing a second bootstrap plane.

## Required work
- wire the validated desktop bootstrap form into the shipped bootstrap runtime:
  - dispatch through the existing `attach_external_target(...)` path with
    `bootstrap=True`
  - preserve the shipped required-field and refusal semantics
- on successful bootstrap:
  - surface explicit success state in the desktop app
  - refresh the attached-target label/view so the new target is visible
  - make the first post-bootstrap next-step guidance explicit, including that
    the target is attached/initialized but still awaits first activation
- on refusal/failure:
  - surface the refusal clearly in the desktop app
  - preserve typed operator context where practical instead of forcing full
    re-entry for ordinary validation/runtime refusals
- preserve the existing explicit refusal behavior for:
  - `partial_target`
  - `malformed_target`
- add or update focused tests for the dispatch and post-bootstrap handoff
  behavior

## Constraints
- Follow `CLAUDE.md`.
- Stay narrowly focused on bootstrap dispatch and immediate post-bootstrap
  handoff.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not silently transition canonical phase/task artifacts.
- Reuse the shipped bootstrap runtime; do not invent a second hidden bootstrap
  implementation.
- Do not add first-phase activation/start behavior.
- Do not invent hidden defaults for `attached_by`, `bootstrapped_by`,
  `human_objective`, or `project_intent`.
- Do not weaken the shipped `partial_target` / `malformed_target` refusal
  behavior.
- Prefer small, testable, reversible changes.

## Important guardrails
- The shipped runtime and canonical artifacts remain the source of truth.
- Bootstrap remains distinct from first-phase activation.
- Do not add hidden background orchestration or a UI-only state plane.
- Keep this slice centered on bounded dispatch and explicit next-step handoff.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- any other focused desktop/bootstrap tests you need to update
- `README.md` if the operator-visible workflow changes

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
