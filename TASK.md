# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated
local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and
  generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the
Codex and Claude loop carry the project forward phase by phase with review,
fixes, and human gating between phases.

## Active Phase

Fix Phase B - Desktop Empty-Target Bootstrap Flow

## Active Sub-Phase

Fix Phase B2 - Desktop Bootstrap Form And Validation

## Phase Status

Fix Phase B1 is complete and approved to advance. Fix Phase B2 is now active
as the next remediation slice focused on turning the approved desktop bootstrap
UX contract into a bounded form-and-validation surface so the desktop app can
collect the required bootstrap inputs safely before any later dispatch slice.

## Active Task

Implement Fix Phase B2 for the agent loop. This slice should add the bounded
desktop bootstrap form, required-field entry flow, and fail-closed validation
surface for empty-target project setup without yet introducing direct desktop
bootstrap dispatch or weakening the shipped attach/bootstrap runtime contract.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Fix Phase B / B2 as active
- `.agent-loop/phase-plan.md` records Fix Phase B1 as closed history and
  contains a
  `## Fix Phase B2 - Desktop Bootstrap Form And Validation`
  section with concrete objective, done criteria, and exclusions
- the repository adds a bounded desktop bootstrap form surface for
  `empty_target` project setup, including explicit required-field capture for
  `attached_by`, `approval_mode`, `bootstrapped_by`, `human_objective`, and
  `project_intent`
- the implementation validates those fields fail-closed in the desktop flow,
  preserves typed operator context on validation failure, and continues to
  refuse `partial_target` and `malformed_target` paths explicitly
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, desktop/UI boundaries, and the
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or a second desktop-only bootstrap state plane
- focused validation proves the bounded form and validation surface is
  explicit, auditable, and does not yet silently dispatch bootstrap mutation
- `README.md` reflects that Fix Phase B2 is active and that desktop bootstrap
  form/validation work is now the implementation focus

## Next-Phase Gate

Do not widen into desktop bootstrap dispatch until:

- Fix Phase B2 receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop form-and-validation slice
- any direct desktop bootstrap dispatch is activated through Fix Phase B3
  instead of being folded into this form/validation slice

## Out Of Scope For Current Phase

- any direct desktop-side dispatch to `attach_external_target(...)` or any
  second hidden bootstrap runtime
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any post-bootstrap activation/start flow, packaging work, hidden
  orchestration, or live automation added under the banner of this validation
  slice
- any rewrite of current shipped behavior just to make future desktop flows
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later bootstrap-dispatch, post-bootstrap handoff, packaging, or
  external sync work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  contract surface
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
