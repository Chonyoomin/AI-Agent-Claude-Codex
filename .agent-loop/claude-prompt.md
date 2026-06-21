# Claude Code Task

## Phase
Phase 10C - External Workspace Bootstrap Contract

## Objective
Define the External Workspace Bootstrap Contract for the agent loop. This slice should specify how target-side `.agent-loop` initialization may occur in external-workspace mode, which canonical artifacts may be created or refused, what operator decisions and bootstrap states must be recorded, and how later Phase 10D/10E runtime slices depend on that bootstrap contract.

## Context
Phase 10 continues the future product-features track. Phase 10C is a planning/contract slice, not a runtime slice: the goal is to define the bootstrap contract before any bootstrap or attach/detach implementation ships, so later runtime work has a concrete initialization boundary, refusal model, and source-of-truth contract instead of inventing bootstrap behavior ad hoc.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10C as active
- `.agent-loop/phase-plan.md` records Phase 10B as closed history and contains a `## Phase 10C - External Workspace Bootstrap Contract` section with concrete objective, done criteria, and exclusions
- define the bootstrap contract, in repo artifacts, for future external-workspace mode:
  - what target-side canonical artifact set may be initialized by bootstrap
  - which partial, malformed, or ambiguous target states must be refused fail-closed
  - what explicit operator opt-in or approval-sensitive inputs are required before bootstrap may proceed
  - what bootstrap-state values, audit expectations, and target/controller ownership boundaries later runtime slices must preserve
  - how later Phase 10D/10E runtime work depends on this contract
- preserve the shipped artifact/source-of-truth boundary:
  - controller-owned attach metadata remains controller-owned
  - target-side canonical artifacts remain target-owned
  - bootstrap must not invent advisory state as canonical truth
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10C is active and that the bootstrap contract is now the implementation focus
- add focused validation sufficient to prove the new contract/docs surface is concrete, consistent, and non-drifting
- do not implement bootstrap runtime or attach/detach runtime behavior in this slice; this phase is contract/planning only

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
- no attach/detach runtime implementation or target-selection runtime behavior
- no bootstrap runtime implementation beyond the contract/planning work for this phase
- no external UI, dashboard, or run-control implementation
- no concurrent Codex/Claude execution implementation, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- no automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- no regression of the shipped Phase 5 review, strict, bounded autonomous, reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation, runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
