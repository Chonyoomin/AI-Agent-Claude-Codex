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

Fix Phase B3 - Desktop Bootstrap Dispatch And Post-Bootstrap Handoff

## Phase Status

Fix Phase B2 is complete and approved to advance. Fix Phase B3 is now active
as the next remediation slice focused on wiring the validated desktop bootstrap
flow into the shipped bootstrap runtime and surfacing the first explicit
post-bootstrap handoff in the desktop app.

## Active Task

Implement Fix Phase B3 for the agent loop. This slice should wire the validated
desktop bootstrap form into the shipped `attach-external-target --bootstrap`
runtime path, refresh the attached-target view after success, and surface the
first explicit post-bootstrap next-step guidance without introducing a second
bootstrap runtime or hidden desktop-only state plane.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Fix Phase B / B3 as active
- `.agent-loop/phase-plan.md` records Fix Phase B2 as closed history and
  contains a
  `## Fix Phase B3 - Desktop Bootstrap Dispatch And Post-Bootstrap Handoff`
  section with concrete objective, done criteria, and exclusions
- the repository dispatches validated desktop bootstrap input through the
  shipped `attach-external-target --bootstrap` runtime path rather than a
  second hidden bootstrap implementation
- the desktop flow surfaces explicit success/refusal state for the bootstrap
  attempt, refreshes the attached-target view after a successful bootstrap, and
  makes the first post-bootstrap next-step guidance explicit
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, desktop/UI boundaries, and the
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or a second desktop-only bootstrap state plane
- focused validation proves the bounded dispatch/handoff surface is explicit,
  auditable, and still routes through the shipped runtime and artifact model
- `README.md` reflects that Fix Phase B3 is active and that desktop bootstrap
  dispatch/post-bootstrap handoff work is now the implementation focus

## Next-Phase Gate

Do not widen into first-phase activation/start automation until:

- Fix Phase B3 receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop bootstrap dispatch/handoff slice
- any first-phase activation or project-start automation is activated through a
  later dedicated phase instead of being folded into this bootstrap slice

## Out Of Scope For Current Phase

- any first-phase activation/start flow that bypasses the shipped Phase 4C
  activator + human approval contract
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any packaging work, hidden orchestration, or live automation added under the
  banner of this bootstrap dispatch slice
- any rewrite of current shipped behavior just to make future desktop flows
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later first-phase activation, packaging, or external sync work
  into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  contract surface
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
