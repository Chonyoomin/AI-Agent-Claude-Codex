# Claude Code Task

## Phase
Phase 10J - Artifact Dashboard Contract

## Objective
Define Phase 10J for the agent loop. This slice should specify how review summaries, diff views, progress history, approval actions, token/cost reporting, and failure analytics should be surfaced in the external UI without replacing canonical artifacts on disk.

## Context
Phase 10J builds directly on the shipped Phase 10G through 10I external UI work. The goal in this slice is not to implement a dashboard runtime yet, but to define the contract that a future dashboard implementation must satisfy: what information it may surface, which values are canonical mirrors versus advisory derived state, how it should present review and progress artifacts, and how it must remain subordinate to the existing CLI-first and canonical-artifact-first workflow.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10J as active
- `.agent-loop/phase-plan.md` records Phase 10I as closed history and contains a `## Phase 10J - Artifact Dashboard Contract` section with concrete objective, done criteria, and exclusions
- add a documentation-first contract for how an external artifact dashboard should surface review summaries, diff views, progress history, approval actions, token/cost reporting, and failure analytics
- define clearly which dashboard values are canonical mirrors versus advisory derived state, and preserve repo artifacts on disk as the source of truth
- preserve the shipped CLI-first workflow and make clear that the dashboard must not become a new unbounded control plane or hidden mutation path
- preserve the shipped approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` activation gate
- update `README.md` so it reflects that Phase 10J is active and that the artifact dashboard contract is now the implementation focus
- add focused validation proving the dashboard contract is bounded, internally consistent with Phase 10G through 10I, and reflected accurately in planning/docs surfaces

Recommended implementation shape for this slice:
- add a new contract doc under `docs/` for the artifact dashboard surface
- use the existing external UI docs and README language as the style/contract baseline
- keep the contract concrete enough that Phase 10K can implement against it without needing another design pass

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update focused tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no artifact dashboard runtime implementation, analytics backend, diff viewer, history explorer, or approval-action runtime beyond the contract itself
- no controlled-concurrency, overlap-safe detection, or concurrent Codex/Claude execution work
- no MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- no automatic next-phase activation behavior that bypasses the shipped Phase 4 planner / activation separation
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
