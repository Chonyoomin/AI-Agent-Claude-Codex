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

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10Z - Model, Policy Pack, And Template Selection UX

## Phase Status

Phase 10Y is complete and approved to advance. Phase 10Z is now active as the
next mainline slice focused on adding the first bounded desktop-managed
selection flow for models, policy packs, and project templates without letting
those choices become a hidden second source of truth.

## Active Task

Implement Phase 10Z for the agent loop. This slice should define and implement
the first bounded desktop-managed selection UX for model choices, policy packs,
project templates, and other high-level run presets without letting those
settings become a hidden second source of truth.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10Z as active
- `.agent-loop/phase-plan.md` records Phase 10Y as closed history and contains
  a `## Phase 10Z - Model, Policy Pack, And Template Selection UX` section with
  concrete objective, done criteria, and exclusions
- the repository adds the first bounded desktop surface for choosing model
  options, policy packs, project templates, and related high-level run presets
- the implementation defines how those selections are derived, displayed, and
  applied through canonical artifacts and explicit operator actions rather than
  hidden UI-only state
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, desktop/UI boundaries, existing run-profile
  semantics, and the Phase 10I library-callable cap instead of introducing
  hidden automation, silent mutation, or a parallel control plane
- focused validation proves the selection UX is bounded, auditable, and scoped
  to operator-visible configuration flows without widening into packaging,
  controlled concurrency, or hidden orchestration
- `README.md` reflects that Phase 10Z is active and that model, policy-pack,
  and template selection UX is now the implementation focus

## Next-Phase Gate

Do not widen model, policy-pack, and template selection beyond a bounded
desktop-managed UX slice until:

- Phase 10Z receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first desktop-managed model/policy/template selection
  slice
- any packaging, controlled-concurrency, or hidden orchestration work is
  activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any hidden model-selection state store, silent preset mutation, or background
  control plane that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any concurrent Codex/Claude overlap execution, packaging work, or hidden
  orchestration added under the banner of selection UX
- any rewrite of current shipped behavior just to make future autonomy work
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later packaging, memory-export, or concurrency work into this
  slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  selection-UX surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
