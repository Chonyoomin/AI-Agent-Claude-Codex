# Claude Code Task

## Phase
Phase 10Z - Model, Policy Pack, And Template Selection UX

## Objective
Implement Phase 10Z for the agent loop. This slice should define and implement
the first bounded desktop-managed selection UX for model choices, policy packs,
project templates, and other high-level run presets without letting those
settings become a hidden second source of truth.

## Context
Implement the Model, Policy Pack, And Template Selection UX slice for the agent
loop. This is the next desktop-runtime step after the shipped Phase 10Y
capacity recovery and resume console. The goal is to make high-level run preset
selection legible and auditable from the desktop app while continuing to treat
canonical artifacts as the source of truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10Z as active
- `.agent-loop/phase-plan.md` records Phase 10Y as closed history and contains
  a `## Phase 10Z - Model, Policy Pack, And Template Selection UX` section with
  concrete objective, done criteria, and exclusions
- add the first bounded desktop surface for selecting model choices, policy
  packs, project templates, and related high-level run presets
- define how those selections are represented, surfaced, and applied through
  canonical artifacts and explicit operator actions without creating hidden
  UI-only state that competes with repo artifacts
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, existing run-profile semantics, and the Phase 10I
  library-callable cap instead of introducing hidden automation, silent
  mutation, or a parallel state store
- add focused validation proving the selection UX path is bounded, auditable,
  and scoped to operator-visible configuration flows
- `README.md` reflects that Phase 10Z is active and that model, policy-pack,
  and template selection UX is now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no hidden model-selection state store, silent preset mutation, or background
  control plane that bypasses the shipped Python runtime
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no concurrent Codex/Claude overlap execution, packaging work, or hidden
  orchestration added under the banner of selection UX
- no rewrite of current shipped behavior just to make future autonomy work
  easier
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
