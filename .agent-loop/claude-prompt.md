# Claude Code Task

## Phase
Phase 10B - External Target Attach Record Contract

## Objective
Define the External Target Attach Record Contract for the agent loop. This slice should specify the controller-owned attach-record schema, what target-selection metadata it must persist, how canonicalized target paths and controller identity are represented, what audit/refusal fields are required, and how later Phase 10 attach/detach runtime slices depend on that record.

## Context
Phase 10 continues the future product-features track. Phase 10B is a planning/contract slice, not a runtime slice: the goal is to define the controller-owned attach record before any attach/detach implementation ships, so later runtime work has a concrete schema, audit model, and refusal boundary instead of inventing metadata ad hoc.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10B as active
- `.agent-loop/phase-plan.md` records Phase 10A as closed history and contains a `## Phase 10B - External Target Attach Record Contract` section with concrete objective, done criteria, and exclusions
- define the attach-record contract, in repo artifacts, for future external-workspace mode:
  - exact schema-stable fields the controller-owned attach record must carry
  - how canonicalized target path, controller identity, attach timestamp, operator identity, and signal/version markers are represented
  - what mode-selection, bootstrap-state, stale-attach detection, and refusal-sensitive metadata must be persisted
  - which fields are canonical versus advisory
  - how later Phase 10C/10D/10E work depends on this record
- preserve the shipped artifact/source-of-truth boundary:
  - the attach record is controller-owned
  - target-side canonical artifacts remain target-owned
  - future runtime/UI surfaces must stay advisory unless the contract explicitly promotes them
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10B is active and that the attach-record contract is now the implementation focus
- add focused validation sufficient to prove the new contract/docs surface is concrete, consistent, and non-drifting
- do not implement attach/detach runtime behavior in this slice; this phase is contract/planning only

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
- no bootstrap runtime implementation
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
