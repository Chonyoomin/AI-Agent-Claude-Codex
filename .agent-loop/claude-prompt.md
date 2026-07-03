# Claude Code Task

## Phase
Phase 10AA - Human-Facing Memory Vault Export Contract And Initial Slice

## Objective
Implement Phase 10AA for the agent loop. This slice should define and implement
the first bounded human-facing memory vault export surface, including optional
human-readable memory views such as decision summaries and architecture
snapshots, without replacing repo artifacts as the primary source of truth.

## Context
Implement the Human-Facing Memory Vault Export slice for the agent loop. This
is the next mainline step after the shipped Phase 10Z selection UX slice. The
goal is to make durable memory and selected canonical mirrors legible and
auditable from an operator-facing surface without letting the export become a
competing source of truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AA as active
- `.agent-loop/phase-plan.md` records Phase 10Z as closed history and contains
  a `## Phase 10AA - Human-Facing Memory Vault Export Contract And Initial Slice`
  section with concrete objective, done criteria, and exclusions
- add the first bounded human-facing memory-vault export surface for durable
  memory entries, decision summaries, and architecture/project snapshots
- define how those exports are represented, labeled, and derived from shipped
  durable-memory and canonical artifacts without creating a competing
  source-of-truth state plane
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, durable-memory ownership semantics, and the existing
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or a parallel state store
- add focused validation proving the memory-vault export path is bounded,
  auditable, and scoped to operator-visible summaries/exports
- `README.md` reflects that Phase 10AA is active and that human-facing
  memory-vault export work is now the implementation focus

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
- no hidden replacement memory store, silent durable-memory mutation, or
  background control plane that bypasses the shipped Python runtime
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no concurrent Codex/Claude overlap execution, packaging work, or hidden
  orchestration added under the banner of memory-vault exports
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
