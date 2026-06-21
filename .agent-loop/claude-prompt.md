# Claude Code Task

## Phase
Phase 10A - External Workspace Controller Contract

## Objective
Define the External Workspace Controller Contract for the agent loop. This slice should specify how the controller repo can target a different workspace or repository safely, what remains controller-owned versus target-owned, where `.agent-loop` artifacts live, how attach/bootstrap and refusal behavior must work, and which later Phase 10 slices implement those behaviors.

## Context
Phase 10 starts the future product-features track. Phase 10A is a planning/contract slice, not an implementation slice: the goal is to define, before any runtime or UI work, how this controller repo can safely target an external workspace or repository without blurring controller-owned artifacts, target-owned artifacts, or shipped safety boundaries.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10A as active
- `.agent-loop/phase-plan.md` records Phase 9G as closed history and contains a `## Phase 10A - External Workspace Controller Contract` section with concrete objective, done criteria, and exclusions
- define the contract, in repo artifacts, for safe external-workspace targeting:
  - what remains controller-owned in this repo
  - what may exist in a target workspace or repository
  - where `.agent-loop` artifacts live in controller and target modes
  - how path resolution, attach/bootstrap, refusal behavior, and approval gates must work
  - how later Phase 10B/10C/10D/10E work depends on this contract
- preserve the shipped artifact/source-of-truth boundary:
  - canonical repo artifacts remain authoritative
  - any future external-workspace metadata, descriptors, or UI surfaces must stay advisory unless the contract explicitly promotes them
- preserve the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- update `README.md` so it reflects that Phase 10A is active and that the external-workspace controller contract is now the implementation focus
- add focused validation sufficient to prove the new contract/docs surface is concrete, consistent, and non-drifting
- do not implement external-workspace runtime behavior in this slice; this phase is contract/planning only

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
- no external workspace bootstrap, attach flow, or target selection runtime
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
