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

Phase 10AA - Human-Facing Memory Vault Export Contract And Initial Slice

## Phase Status

Phase 10Z is complete and approved to advance. Phase 10AA is now active as the
next mainline slice focused on defining and shipping the first bounded
human-facing memory vault export surface without replacing repo artifacts as
the primary source of truth.

## Active Task

Implement Phase 10AA for the agent loop. This slice should define and implement
the first bounded human-facing memory vault export surface, including optional
human-readable memory views such as decision summaries and architecture
snapshots, without replacing repo artifacts as the primary source of truth.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AA as active
- `.agent-loop/phase-plan.md` records Phase 10Z as closed history and contains
  a `## Phase 10AA - Human-Facing Memory Vault Export Contract And Initial Slice`
  section with concrete objective, done criteria, and exclusions
- the repository adds the first bounded human-facing memory-vault export
  surface for durable memory entries, decision summaries, and architecture /
  project snapshots
- the implementation defines how those exports are derived from existing
  canonical and durable-memory artifacts, labeled as advisory or canonical
  mirrors, and kept distinct from the source-of-truth repo files
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, desktop/UI boundaries, existing run-profile
  semantics, durable-memory ownership boundaries, and the existing
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or a parallel control plane
- focused validation proves the memory-vault export surface is bounded,
  auditable, and scoped to operator-visible summaries/exports without widening
  into packaging, controlled concurrency, or hidden orchestration
- `README.md` reflects that Phase 10AA is active and that human-facing
  memory-vault export work is now the implementation focus

## Next-Phase Gate

Do not widen human-facing memory-vault exports beyond a bounded initial slice
until:

- Phase 10AA receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first bounded memory-vault export slice
- any richer vault tooling, external sync, packaging, or controlled-concurrency
  work is activated through its own later phase instead of being folded into
  this slice

## Out Of Scope For Current Phase

- any hidden replacement memory store, silent durable-memory mutation, or
  background control plane that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any concurrent Codex/Claude overlap execution, packaging work, or hidden
  orchestration added under the banner of memory-vault exports
- any rewrite of current shipped behavior just to make future autonomy work
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later packaging, external sync, or concurrency work into this
  slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  memory-vault export surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
